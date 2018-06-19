import string
import random
import os
import shutil

import sqlite3

from data_management.image_manipulations import is_image

class ImgDatabaseHandler():
    """NOTE: Don't use this code in production without cleaning the input on the table name!"""
    def __init__(self, db_root):
        self.db = sqlite3.connect(db_root)
        self.cursor = self.db.cursor()
        self.previous_img_path = None
        self.previous_geo = None
        self.previous_time = None

    def create_img_table(self, name):
        try:
            self.cursor.execute(f'''CREATE TABLE IF NOT EXISTS
                                    {name}(img_id VARCHAR PRIMARY KEY, lat REAL, long REAL, datetime VARCHAR, class STRING)''')
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    def store_image_details(self, target_table, image_class, img_path, location, time, autocommit=True):
        try:
            self.db.execute(f'INSERT INTO {target_table} VALUES (?,?,?,?,?)', [img_path, location[0], location[1], time, image_class])
            if autocommit:
                self.db.commit()
        except sqlite3.IntegrityError as e:
            print(f'Cannot store image details: {e}')
    
    def remove_record(self, target_table, img_path):
        try:
            self.db.execute(f'DELETE FROM {target_table} WHERE img_id=(?)', [img_path])
            self.db.commit()
        except sqlite3.IntegrityError as e:
            print(f'Cannot delete record: {e}')
    
    def get_all_records(self, table):
        try:
            return([record for record in self.cursor.execute(f'SELECT * FROM {table}')])
        except sqlite3.IntegrityError as e:
            print(f'Cannot load records: {e}')
    
    def calculate_splits(self, table, field_name, split_probabilities, commit_interval=50):
        records = self.get_all_records(table)
        for i, record in enumerate(records):
            split = determine_split(split_probabilities)
            try:
                self.db.execute(f'UPDATE {table} SET {field_name}=(?) WHERE img_id=(?)', [split, record[0]])
                if i % commit_interval == 0 or i == len(records):
                    self.db.commit()
            except sqlite3.IntegrityError as e:
                print(f'Cannot load records: {e}')
                
    def add_field(self, table, field_name):
        try:
            self.db.execute(f'ALTER TABLE {table} ADD COLUMN {field_name} INTEGER;')
        except sqlite3.IntegrityError as e:
            self.db.rollback()
            print(f'Cannot add split field: {e}')

def determine_split(split_probs):
    if not split_probs['train'] + split_probs['val'] + split_probs['test'] == 100:
        raise AssertionError("Splits don't sum to 100%")
    rand_num = random.randint(1, 100)
    if rand_num < split_probs['train']:
        split = 'train'
    elif rand_num <= (split_probs['train'] + split_probs['val']):
        split = 'val'
    else:
        split = 'test'
    return(split)

def create_dir_if_not_exist(directory):
    """Creates a directory if the path does not yet exist.

    Args:
        directory (string): The directory to create.
    """          
    if not os.path.exists(directory):
        os.makedirs(directory)

def generate_random_filename(length=10):
    # https://www.pythoncentral.io/python-snippets-how-to-generate-random-string/
    allchar = string.ascii_letters + string.digits
    return("".join(random.choice(allchar) for x in range(length)))

def create_dataloader_folders(root_dir, data_folder_name, classes):
    """For a given root dir, creates a folder structure which matches the PyTorch dataloader format"""
    data_root = os.path.join(root_dir, data_folder_name)
    create_dir_if_not_exist(data_root)
    splits = ['train', 'val', 'test']
    for split in splits:
        split_folder = os.path.join(data_root, split)
        create_dir_if_not_exist(split_folder)
        for c in classes:
            class_folder = os.path.join(split_folder, c)
            create_dir_if_not_exist(class_folder)

def randomly_sample_from_folder(folder_in, folder_out, retain_every_n, seed=1):
    """For a given folder, shuffles the folder and retains every nth image"""
    random.seed(seed)
    files_in_root = next(os.walk(folder_in))[2]
    random.shuffle(files_in_root)
    create_dir_if_not_exist(folder_out)
    n_imgs = 0
    for i, image in enumerate(files_in_root):
        if (n_imgs+1) % retain_every_n == 0:
            if is_image(image):
                in_img_path = os.path.join(folder_in, image)
                out_img_path = os.path.join(folder_out, image)
                shutil.copy(in_img_path, out_img_path)
                n_imgs += 1

def save_n_images_from_dir(dir_in, target_dir, retain_n_total, seed=1):
    create_dir_if_not_exist(target_dir)
    random.seed(seed)
    images = []
    for root, _, files in os.walk(dir_in):
        images += [os.path.join(root, file) for file in files if is_image(file)]
    random.shuffle(images)
    selected_imgs = random.sample(images,retain_n_total)
    for i, image in enumerate(selected_imgs):
        img_name = os.path.basename(image)
        out_path = os.path.join(target_dir, img_name)
        shutil.copy(image, out_path)
        if i % 1000 == 0:
            print(i)

