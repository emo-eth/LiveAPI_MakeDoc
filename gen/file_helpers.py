import os


def create_directory_with_init(directory_path: str):
    """
    Create a directory if it doesn't exist and add __init__.py files to all folders in the path if they don't exist.
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)


def create_file(folder_path: str, file_name: str):
    create_directory_with_init(folder_path)
    file_path = os.path.join(folder_path, file_name)
    with open(file_path, "a"):
        pass
