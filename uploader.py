import os, random, asyncio, subprocess, shutil, time
from telethon import functions
from telethon.tl.types import InputPeerSelf, InputMediaUploadedDocument, DocumentAttributeFilename
import telethon.tl.types as types

PARALLEL = 4
CHUNK = 512 * 1024
DELAY_MIN, DELAY_MAX = 10, 20

async def hyper_upload_file(client, file_path):
    size = os.path.getsize(file_path)
    total_parts = (size + CHUNK - 1) // CHUNK
    file_id = int.from_bytes(os.urandom(8), 'big', signed=True)
    is_big = size > 10*1024*1024
    uploaded = 0
    sem = asyncio.Semaphore(PARALLEL)
    start = time.time()
    last_print = 0

    async def upload_part(idx, chunk):
        nonlocal uploaded
        async with sem:
            if is_big:
                await client(functions.upload.SaveBigFilePartRequest(file_id=file_id, file_part=idx, file_total_parts=total_parts, bytes=chunk))
            else:
                await client(functions.upload.SaveFilePartRequest(file_id=file_id, file_part=idx, bytes=chunk))
            uploaded += len(chunk)
            if time.time() - last_print > 0.5:
                elapsed = time.time() - start
                speed = uploaded / elapsed if elapsed else 0
                pct = (uploaded / size) * 100
                spd = f"{speed/(1024**2):.2f} MB/s" if speed > 1024**2 else f"{speed/1024:.2f} KB/s"
                eta = time.strftime("%H:%M:%S", time.gmtime((size-uploaded)/speed)) if speed else "calc..."
                print(f"\r   🚀 Uploading: {pct:.2f}% | Speed: {spd} | ETA: {eta}    ", end='')

    tasks = []
    with open(file_path, 'rb') as f:
        for i in range(total_parts):
            chunk = f.read(CHUNK)
            if not chunk: break
            tasks.append(upload_part(i, chunk))
    await asyncio.gather(*tasks)
    print("\n   📦 Processing...")
    return file_id, total_parts, is_big

async def upload_single_file_logic(client, file, caption_prefix):
    size = os.path.getsize(file)
    max_size = 1950 * 1024 * 1024
    files_to_upload = []
    if size > max_size:
        print(f"⚠️ File >2GB, splitting...")
        subprocess.run(f'split -b 1950M "{file}" "{file}.part"', shell=True)
        os.remove(file)
        files_to_upload = sorted([f for f in os.listdir('.') if f.startswith(f"{file}.part")])
    else:
        files_to_upload = [file]
    for idx, f in enumerate(files_to_upload, 1):
        caption = f"{caption_prefix}\nPart: {idx}/{len(files_to_upload)}"
        print(f"\n⚡ Uploading piece {idx}/{len(files_to_upload)} : '{f}'")
        file_id, total_parts, is_big = await hyper_upload_file(client, f)
        peer = InputPeerSelf()
        attrs = [DocumentAttributeFilename(file_name=f)]
        if is_big:
            media = InputMediaUploadedDocument(file=types.InputFileBig(id=file_id, parts=total_parts, name=f), mime_type='application/octet-stream', attributes=attrs)
        else:
            media = InputMediaUploadedDocument(file=types.InputFile(id=file_id, parts=total_parts, name=f, md5_checksum=''), mime_type='application/octet-stream', attributes=attrs)
        await client(functions.messages.SendMediaRequest(peer=peer, media=media, message=caption, random_id=int.from_bytes(os.urandom(8), 'big', signed=True)))
        print(f"\n✅ Uploaded.")
        if os.path.exists(f): os.remove(f)
        await asyncio.sleep(random.randint(DELAY_MIN, DELAY_MAX))

async def process_downloaded_item(client, path, is_folder, caption_prefix):
    if is_folder:
        print(f"\n📂 Processing folder: {path}")
        all_files = []
        for root, _, files in os.walk(path):
            for f in files:
                all_files.append(os.path.join(root, f))
        if not all_files:
            print("⚠️ Empty folder.")
            shutil.rmtree(path, ignore_errors=True)
            return
        print(f"📁 Found {len(all_files)} files.")
        for idx, fp in enumerate(all_files, 1):
            rel = os.path.relpath(fp, path)
            safe = rel.replace(os.sep, '_')
            shutil.move(fp, safe)
            print(f"\n📄 [{idx}/{len(all_files)}] Uploading: {safe}")
            await upload_single_file_logic(client, safe, f"{caption_prefix}\nFile {idx}/{len(all_files)}")
        shutil.rmtree(path, ignore_errors=True)
    else:
        print(f"\n📄 Single file: {path}")
        await upload_single_file_logic(client, str(path), caption_prefix)