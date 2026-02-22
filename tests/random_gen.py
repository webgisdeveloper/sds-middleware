import os
import random

def generate_random_files(filename_list_file):
    # Constants for sizes in bytes
    MIN_SIZE = 200 * 1024       # 200 KB
    MAX_SIZE = 10 * 1024 * 1024  # 10 MB

    try:
        with open(filename_list_file, 'r') as f:
            # Strip whitespace and ignore empty lines
            filenames = [line.strip() for line in f if line.strip()]
        
        if not filenames:
            print("The text file is empty. No files to create.")
            return

        for name in filenames:
            # Determine a random size for this specific file
            file_size = random.randint(MIN_SIZE, MAX_SIZE)
            
            # Generate and write random bytes
            with open(name, 'wb') as fout:
                fout.write(os.urandom(file_size))
            
            print(f"Created {name} ({file_size / 1024:.2f} KB)")
            
        print("\nAll files generated successfully!")

    except FileNotFoundError:
        print(f"Error: The file '{filename_list_file}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Run the script
if __name__ == "__main__":
    # Change 'files.txt' to the name of your actual text file
    generate_random_files('random_file.txt')