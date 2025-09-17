from PIL import Image
import os
import glob
import random
import json
import shutil
from tqdm import tqdm
import numpy as np


def overlay_random_sprite_on_background(
    sprite_folder,
    background_folder,
    output_folder,
    metadata_file,
    num_images=10000
):
    metadata = []

    sprite_paths = [os.path.join(sprite_folder, f) for f in os.listdir(sprite_folder) if f.lower().endswith('png')]
    background_paths = [os.path.join(background_folder, f) for f in os.listdir(background_folder) if f.lower().endswith(('png'))]

    assert sprite_paths, "No sprite images found!"
    assert background_paths, "No background images found!"

    for i in tqdm(range(num_images), desc="Generating composite images"):
        bg_path = random.choice(background_paths)
        sprite_path = random.choice(sprite_paths)

        bg = Image.open(bg_path).convert("RGBA")
        sprite = Image.open(sprite_path).convert("RGBA")
        bg_w, bg_h = bg.size

        new_w = bg_w // 2
        new_h = bg_h // 2
        sprite = sprite.resize((new_w, new_h), Image.LANCZOS)

        max_x = bg_w - new_w
        max_y = bg_h - new_h
        x = random.randint(0, max_x)
        y = random.randint(0, max_y)

        bg_copy = bg.copy()
        bg_copy.paste(sprite, (x, y), sprite)

        filename = f"composite_{i:05}.png"
        output_path = os.path.join(output_folder, filename)
        bg_copy.save(output_path)

        bbox = {
            "image": filename,
            "sprite_source": os.path.basename(sprite_path),
            "background_source": os.path.basename(bg_path),
            "bbox": [x, y, x + new_w, y + new_h]
        }
        metadata.append(bbox)

    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Done! {num_images} images saved to '{output_folder}', metadata in '{metadata_file}'.")

def preprocess_fk_sprites(image_path, output_path, threshold=220):
    img = Image.open(image_path).convert("RGBA")
    data = np.array(img)
    r, g, b, a = data[..., 0], data[..., 1], data[..., 2], data[..., 3]
    white_mask = (r > threshold) & (g > threshold) & (b > threshold)
    data[..., 3][white_mask] = 0
    Image.fromarray(data).save(output_path)


def process_folder(input_folder, output_folder, threshold=220):

    # Supported image formats
    supported_formats = ('*.png')

    for ext in supported_formats:
        for file_path in glob.glob(os.path.join(input_folder, ext)):
            filename = os.path.basename(file_path)
            output_path = os.path.join(output_folder, filename)
            print(f"Processing {filename}...")
            preprocess_fk_sprites(file_path, output_path, threshold)

    print("Done processing all images.")


def convert_to_yolo(json_file, label_output_dir, image_dir, class_id=0):

    with open(json_file, "r") as f:
        data = json.load(f)

    for item in tqdm(data, desc="Converting to YOLO"):
        img_path = os.path.join(image_dir, item['image'])
        if not os.path.exists(img_path):
            continue 
        from PIL import Image
        img = Image.open(img_path)
        img_w, img_h = img.size
        x_min, y_min, x_max, y_max = item['bbox']
        x_center = (x_min + x_max) / 2 / img_w
        y_center = (y_min + y_max) / 2 / img_h
        width = (x_max - x_min) / img_w
        height = (y_max - y_min) / img_h
        label_filename = os.path.splitext(item['image'])[0] + '.txt'
        label_path = os.path.join(label_output_dir, label_filename)

        with open(label_path, "w") as out_f:
            out_f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

    print(f"YOLO labels saved to: {label_output_dir}")


def split_dataset(images_dir, labels_dir, output_dir, split_ratio=0.8):

    files = [f for f in os.listdir(images_dir) if f.endswith('.png')]
    random.shuffle(files)

    split_idx = int(len(files) * split_ratio)
    train_files = files[:split_idx]
    val_files = files[split_idx:]

    for f in tqdm(train_files, desc="Copying Training data..."):
        shutil.copy(os.path.join(images_dir, f), os.path.join(output_dir, "images/train", f))
        shutil.copy(os.path.join(labels_dir, f.replace('.png', '.txt')), os.path.join(output_dir, "labels/train", f.replace('.png', '.txt')))

    for f in tqdm(val_files, "Copying Validation data..."):
        shutil.copy(os.path.join(images_dir, f), os.path.join(output_dir, "images/val", f))
        shutil.copy(os.path.join(labels_dir, f.replace('.png', '.txt')), os.path.join(output_dir, "labels/val", f.replace('.png', '.txt')))

    print("Dataset split into train/val")
