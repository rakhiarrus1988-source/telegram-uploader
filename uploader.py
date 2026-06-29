import os
import random
import asyncio
import subprocess
import shutil
import time
from telethon import functions
from telethon.tl.types import InputPeerSelf, InputMediaUploadedDocument, DocumentAttributeFilename
import telethon.tl.types as types

# ---------------------- SAFE LIMITS (Free Accounts) ----------------------
PARALLEL_CONNECTIONS = 4        # Safe for free accounts
CHUNK_SIZE = 512 * 1024         # 512 KB (stable)
HUMAN_DELAY_MIN = 10            # Minimum delay (seconds)
HUMAN_DELAY_MAX = 20            # Maximum delay
# -----------------------------------------------------------------------

async def hyper_upload_file(client, file_path):
    file_size = os.path.getsize(file_path)
    chunk_size = CHUNK_SIZE
    total_parts = (file_size + chunk_size - 1) // chunk_size
    file_id = int.from_bytes(os.urandom(8), byteorder='big', signed=True)
    is_big = file_size > 10 * 1024 * 1024

    print(f"   📥 Uploading to Saved Messages...")
    uploaded_bytes = 0
    semaphore = asyncio.Semaphore(PARALLEL_CONNECTIONS)
    start_time = time.time()
    last_print_time = 0

    async def upload_part(part_index, chunk_data):
        nonlocal uploaded_bytes
        async with semaphore:
            if is_big:
                await client(functions.upload.SaveBigFilePartRequest(
                    file_id=file_id,
                    file_part=part_index,
                    file_total_parts=total_parts,
                    bytes=chunk_data
                ))
            else:
                await client(functions.upload.SaveFilePartRequest(
                    file_id=file_id,
                    file_part=part_index,
                    bytes=chunk_data
                ))
            uploaded_bytes += len(chunk_data)
            
            if time.time() - last_print_time > 0.5:
                elapsed = time.time() - start_time
                speed = uploaded_bytes / elapsed if elapsed > 0 else 0
                percentage = (uploaded_bytes / file_size) * 100
                
                if speed > 1024**2:
                    speed_str = f"{speed/(1024**2):.2f} MB/s"
                elif speed > 1024:
                    speed_str = f"{speed/1024:.2f} KB/s"
                else:
                    speed_str = f"{speed:.2f} B/s"
                
                if speed > 0:
                    remaining = (file_size - uploaded_bytes) / speed
                    eta = time.strftime("%H:%M:%S", time.gmtime(remaining))
                else:
                    eta = "calculating..."
                
                print(f'\r   🚀 Uploading: {percentage:.2f}%  |  Speed: {speed_str}  |  ETA: {eta}    ', end='')
                last_print_time = time.time()

    tasks = []
    with open(file_path, 'rb') as f:
        for part_index in range(total_parts):
            chunk = f.read(chunk_size)
            if not chunk:
                break
            tasks.append(upload_part(part_index, chunk))

    await asyncio.gather(*tasks)
    print("\n   📦 Processing file in Telegram servers...")
    return file_id, total_parts, is_big

async def upload_single_file_logic(client, original_file, caption_prefix):
    file_size_bytes = os.path.getsize(original_file)
    max_size_bytes = 1950 * 1024 * 1024
    files_to_upload = []

    if file_size_bytes > max_size_bytes:
        print(f"⚠️ File >2GB, splitting into 1.9GB parts...")
        split_command = f'split -b 1950M "{original_file}" "{original_file}.part"'
        subprocess.run(split_command, shell=True)
        os.remove(original_file)
        files_to_upload = sorted([f for f in os.listdir('.') if f.startswith(f"{original_file}.part")])
    else:
        files_to_upload = [original_file]

    total_parts_count = len(files_to_upload)
    for index, current_file in enumerate(files_to_upload, start=1):
        caption_text = f"{caption_prefix}\nPart: {index}/{total_parts_count}"
        print(f"\n⚡ Uploading piece {index}/{total_parts_count} : '{current_file}'")

        file_id, total_parts, is_big = await hyper_upload_file(client, current_file)
        peer = InputPeerSelf()
        attributes = [DocumentAttributeFilename(file_name=current_file)]

        if is_big:
            media = InputMediaUploadedDocument(
                file=types.InputFileBig(id=file_id, parts=total_parts, name=current_file),
                mime_type='application/octet-stream',
                attributes=attributes
            )
        else:
            media = InputMediaUploadedDocument(
                file=types.InputFile(id=file_id, parts=total_parts, name=current_file, md5_checksum=''),
                mime_type='application/octet-stream',
                attributes=attributes
            )

        await client(functions.messages.SendMediaRequest(
            peer=peer,
            media=media,
            message=caption_text,
            random_id=int.from_bytes(os.urandom(8), byteorder='big', signed=True)
        ))
        print(f"\n✅ File Piece uploaded successfully.")

        if os.path.exists(current_file):
            os.remove(current_file)

        sleep_time = random.randint(HUMAN_DELAY_MIN, HUMAN_DELAY_MAX)
        print(f"💤 Human-like delay: {sleep_time}s")
        await asyncio.sleep(sleep_time)

async def process_downloaded_item(client, item_path, is_folder, caption_prefix):
    if is_folder:
        print(f"\n📂 Processing folder: {item_path}")
        all_files = []
        for root, dirs, files in os.walk(item_path):
            for f in files:
                full_path = os.path.join(root, f)
                all_files.append(full_path)

        total = len(all_files)
        if total == 0:
            print("⚠️ Folder is empty. Nothing to upload.")
            shutil.rmtree(item_path, ignore_errors=True)
            return

        print(f"📁 Found {total} file(s) inside the folder:")
        for idx, fpath in enumerate(all_files, start=1):
            rel_path = os.path.relpath(fpath, item_path)
            print(f"   {idx}. {rel_path}")

        for idx, file_path in enumerate(all_files, start=1):
            relative_path = os.path.relpath(file_path, item_path)
            safe_name = relative_path.replace(os.sep, '_')
            shutil.move(file_path, safe_name)
            print(f"\n📄 [{idx}/{total}] Uploading: {safe_name} (original: {relative_path})")

            await upload_single_file_logic(
                client,
                safe_name,
                f"{caption_prefix}\nFile {idx}/{total}"
            )

        shutil.rmtree(item_path, ignore_errors=True)

    else:
        print(f"\n📄 Processing single file: {item_path}")
        await upload_single_file_logic(client, str(item_path), caption_prefix)