import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os


def reverse_bits(byte):
    """Reverse the bits in a single byte (8 bits)."""
    reversed_byte = 0
    for i in range(8):
        if byte & (1 << i):
            reversed_byte |= (1 << (7 - i))
    return reversed_byte


def generate_xbm_data(ttf_path, char_list, forced_height, max_width, canvas_width, canvas_height,
                      threshold_value=128, padding_top=0, padding_bottom=0):
    """
    Generates XBM data for characters, ensuring proper alignment within grids, narrow character handling, and padding.
    """
    font_size = forced_height * 2
    font = ImageFont.truetype(ttf_path, font_size)
    all_xbm_data = {}

    punctuation_set = {',', '.'}
    punctuation_scale = 0.25
    narrow_chars = {"I"}
    narrow_char_scale = 0.5

    grid_width = 17 if canvas_width == 32 and canvas_height == 64 else canvas_width
    grid_height = 39 if canvas_width == 32 and canvas_height == 64 else canvas_height

    for char in char_list:
        try:
            if char == " ":
                xbm_data = [
                    [0x00 for _ in range(canvas_width // 8)]  # Ensure empty grid for space character
                    for _ in range(canvas_height)
                ]
                all_xbm_data[char] = xbm_data
                continue

            (width, height), (offset_x, offset_y) = font.font.getsize(char)
            if width == 0 or height == 0:
                continue

            image = Image.new('L', (width, height), 0)
            draw = ImageDraw.Draw(image)
            draw.text((-offset_x, -offset_y), char, font=font, fill=255)

            if char in punctuation_set:
                target_height = int(forced_height * punctuation_scale)
                aspect_ratio = width / height
                scaled_width = min(int(target_height * aspect_ratio), max_width)
            elif char in narrow_chars:
                target_height = forced_height
                aspect_ratio = width / height
                scaled_width = min(int(target_height * aspect_ratio * narrow_char_scale), max_width)
            else:
                target_height = forced_height
                aspect_ratio = width / height
                scaled_width = min(int(target_height * aspect_ratio), max_width)

            img_resized = image.resize((scaled_width, target_height), Image.Resampling.LANCZOS)
            binary_array = (np.array(img_resized) > threshold_value).astype(np.uint8)

            padded_array = np.zeros((canvas_height, canvas_width), dtype=np.uint8)

            if canvas_width == 32 and canvas_height == 64:
                vertical_offset = max((grid_height - binary_array.shape[0]) // 2, 0)
                horizontal_offset = max((grid_width - binary_array.shape[1]) // 2, 0)
                # Ensure binary_array fits within the grid
                padded_array[vertical_offset:vertical_offset + binary_array.shape[0],
                             horizontal_offset:horizontal_offset + binary_array.shape[1]] = binary_array
            else:
                vertical_start = padding_top
                horizontal_padding = (canvas_width - scaled_width) // 2
                padded_array[vertical_start:vertical_start + target_height,
                             horizontal_padding:horizontal_padding + scaled_width] = binary_array

            xbm_data = []
            for row in padded_array:
                row_bytes = []
                for byte_index in range(0, canvas_width, 8):
                    byte = 0
                    for bit_index in range(8):
                        col = byte_index + bit_index
                        if col < canvas_width and row[col]:
                            byte |= (1 << (7 - bit_index))
                    row_bytes.append(reverse_bits(byte))
                xbm_data.append(row_bytes)

            all_xbm_data[char] = xbm_data

        except Exception as e:
            print(f"Warning: Unable to process character '{char}'. Reason: {e}")

    return all_xbm_data

def write_xbm(all_xbm_data, output_file, canvas_width, canvas_height):
    """
    Writes XBM data to a file, including both normal and strikeout versions.
    """
    def add_strikeout(xbm_data, canvas_width, canvas_height):
        """
        Adds a strikeout with three lines across the middle of the character.
        Centered relative to the grid for both configurations.
        """
        strikeout_data = []
        grid_width = 17 if canvas_width == 32 and canvas_height == 64 else canvas_width
        grid_height = 39 if canvas_width == 32 and canvas_height == 64 else canvas_height

        middle_start = (grid_height // 2) - 1
        middle_end = middle_start + 3  # Draw 3 rows

        for i, row_bytes in enumerate(xbm_data):
            if middle_start <= i < middle_end:
                new_row = [0xFF] * len(row_bytes)
            else:
                new_row = row_bytes[:]
            strikeout_data.append(new_row)

        return strikeout_data

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# XBM File\n\n")

        normal_data = []
        strikeout_data = []
       

        for char, xbm_data in all_xbm_data.items():
            normal_data.append((char, xbm_data))
            strikeout_data.append((char, add_strikeout(xbm_data, canvas_width, canvas_height)))

        # Write normal characters
        for char, xbm_data in normal_data:
            f.write(f"/* Character: '{char}' */\n")
            f.write(f"#define {char}_width {canvas_width}\n")
            f.write(f"#define {char}_height {canvas_height}\n")
            f.write(f"static char {char}_bits[] = {{\n")

            for row_bytes in xbm_data:
                f.write("  " + ", ".join(f"0x{byte:02X}" for byte in row_bytes) + ",\n")

            f.write("};\n\n")

        # Write strikeout characters
        for char, strikeout in strikeout_data:
            f.write(f"/* Strikeout Character: '{char}' */\n")
            f.write(f"static char {char}_strikeout_bits[] = {{\n")

            for row_bytes in strikeout:
                f.write("  " + ", ".join(f"0x{byte:02X}" for byte in row_bytes) + ",\n")

            f.write("};\n\n")

    print(f"XBM file saved as {output_file}")


# def write_mif(all_xbm_data, output_file, canvas_width, canvas_height):
#     """
#     Writes MIF data to a file, including both normal and strikeout versions.
#     """
#     def add_strikeout(xbm_data, canvas_width, canvas_height):
#         """
#         Adds a strikeout with three lines across the middle of the character.
#         Centered relative to the grid for both configurations.
#         """
#         strikeout_data = []
#         grid_width = 17 if canvas_width == 32 and canvas_height == 64 else canvas_width
#         grid_height = 39 if canvas_width == 32 and canvas_height == 64 else canvas_height

#         middle_start = (grid_height // 2) - 1
#         middle_end = middle_start + 3  # Draw 3 rows

#         for i, row_bytes in enumerate(xbm_data):
#             if middle_start <= i < middle_end:
#                 new_row = [0xFF] * len(row_bytes)
#             else:
#                 new_row = row_bytes[:]
#             strikeout_data.append(new_row)

#         return strikeout_data

#     with open(output_file, "w", encoding="utf-8") as f:
#         # Write MIF header
#         depth = 8192 if canvas_width == 16 and canvas_height == 32 else 16384
#         f.write(f"DEPTH = {depth};\n")
#         f.write(f"WIDTH = {canvas_width};\n")
#         f.write("ADDRESS_RADIX = HEX;\n")
#         f.write("DATA_RADIX = HEX;\n")
#         f.write("CONTENT BEGIN\n\n")

#         address = 0x0000
#         normal_data = []
#         strikeout_data = []
#         strikeout_start_address = depth //2

#         for char, xbm_data in all_xbm_data.items():
#             normal_data.append((char, xbm_data))
#             strikeout_data.append((char, add_strikeout(xbm_data, canvas_width, canvas_height)))

#         # Write normal characters
#         for char, xbm_data in normal_data:
#             f.write(f"-- Character: '{char}'\n")
#             for row_bytes in xbm_data:
#                 word = "".join(f"{byte:02X}" for byte in row_bytes)
#                 f.write(f"{address:04X} : {word};\n")
#                 address += 1

#         # Write strikeout characters
#         address = strikeout_start_address 
#         for char, strikeout in strikeout_data:
#             f.write(f"-- Strikeout Character: '{char}'\n")
#             for row_bytes in strikeout:
#                 word = "".join(f"{byte:02X}" for byte in row_bytes)
#                 f.write(f"{address:04X} : {word};\n")
#                 address += 1

#         f.write("END;\n")

#     print(f"MIF file saved as {output_file}")

def write_mif(all_xbm_data, output_file, canvas_width, canvas_height, mif_output=None):
    """
    Writes MIF data to a file, including both normal and strikeout versions.
    For 32x64, it splits the output into two separate 16x64 MIF files for Low and High.
    Optionally stores all output lines into `mif_output` for further processing.
    """
    def add_strikeout(xbm_data, canvas_width, canvas_height, is_space=False):
        if is_space:
            return [[0x00 for _ in range(canvas_width // 8)] for _ in range(canvas_height)]

        strikeout_data = []
        middle_start = (canvas_height // 2) - 1
        middle_end = middle_start + 3

        for i, row_bytes in enumerate(xbm_data):
            if middle_start <= i < middle_end:
                new_row = [0xFF] * len(row_bytes)
            else:
                new_row = row_bytes[:]
            strikeout_data.append(new_row)
        return strikeout_data

    def append_to_output(output_list, line):
        """Helper to append a line to both file and the output array."""
        output_list.append(line + "\n")

    output_dir = os.path.dirname(output_file)

    if mif_output is None:
        mif_output = []

    with open(output_file, "w", encoding="utf-8") as f:
        # Write MIF header
        header = [
            f"DEPTH = {8192 if canvas_width == 16 and canvas_height == 32 else 16384};",
            f"WIDTH = {canvas_width};",
            "ADDRESS_RADIX = HEX;",
            "DATA_RADIX = HEX;",
            "CONTENT BEGIN\n"
        ]
        for line in header:
            f.write(line + "\n")
            append_to_output(mif_output, line)

        address = 0x0000
        strikeout_start_address = 8192 if canvas_width == 16 and canvas_height == 32 else 16384 // 2

        # Prepare data for normal and strikeout characters
        normal_data = []
        strikeout_data = []

        for char, xbm_data in all_xbm_data.items():
            is_space = (char == " ")
            normal_data.append((char, xbm_data))
            strikeout_data.append((char, add_strikeout(xbm_data, canvas_width, canvas_height, is_space)))

        # Write normal characters
        for char, xbm_data in normal_data:
            f.write(f"-- Character: '{char}'\n")
            append_to_output(mif_output, f"-- Character: '{char}'")
            for row_bytes in xbm_data:
                word = "".join(f"{byte:02X}" for byte in row_bytes)
                line = f"{address:04X} : {word};"
                f.write(line + "\n")
                append_to_output(mif_output, line)
                address += 1

        # Write strikeout characters
        address = strikeout_start_address
        for char, xbm_data in strikeout_data:
            f.write(f"-- Strikeout Character: '{char}'\n")
            append_to_output(mif_output, f"-- Strikeout Character: '{char}'")
            for row_bytes in xbm_data:
                word = "".join(f"{byte:02X}" for byte in row_bytes)
                line = f"{address:04X} : {word};"
                f.write(line + "\n")
                append_to_output(mif_output, line)
                address += 1

        f.write("END;\n")
        append_to_output(mif_output, "END;")

    print(f"MIF file saved as {output_file}")

    if canvas_width == 32 and canvas_height == 64:
        # Split into Low and High files with comments intact
        low_output_file = os.path.join(output_dir, "FontRom16x64_Low.mif")
        high_output_file = os.path.join(output_dir, "FontRom16x64_High.mif")

        low_content = []
        high_content = []

        # Prepare Low and High content with comments
        address = 0x0000
        for char, xbm_data in normal_data:
            low_content.append(f"-- Character: '{char}'")
            high_content.append(f"-- Character: '{char}'")
            for row_bytes in xbm_data:
                word = "".join(f"{byte:02X}" for byte in row_bytes)
                low_content.append(f"{address:04X} : {word[4:8]};")
                high_content.append(f"{address:04X} : {word[0:4]};")
                address += 1

        # Write strikeout characters to split files
        address = 0x2000
        for char, xbm_data in strikeout_data:
            low_content.append(f"-- Strikeout Character: '{char}'")
            high_content.append(f"-- Strikeout Character: '{char}'")
            for row_bytes in xbm_data:
                word = "".join(f"{byte:02X}" for byte in row_bytes)
                low_content.append(f"{address:04X} : {word[4:8]};")
                high_content.append(f"{address:04X} : {word[0:4]};")
                address += 1

        # Finalize both Low and High content
        low_content.append("END;")
        high_content.append("END;")

        # Write Low file
        with open(low_output_file, "w", encoding="utf-8") as low_f:
            low_f.write(f"DEPTH = 16384;\nWIDTH = 16;\nADDRESS_RADIX = HEX;\nDATA_RADIX = HEX;\nCONTENT BEGIN\n\n")
            low_f.write("\n".join(low_content))
        print(f"Low split MIF saved: {low_output_file}")

        # Write High file
        with open(high_output_file, "w", encoding="utf-8") as high_f:
            high_f.write(f"DEPTH = 16384;\nWIDTH = 16;\nADDRESS_RADIX = HEX;\nDATA_RADIX = HEX;\nCONTENT BEGIN\n\n")
            high_f.write("\n".join(high_content))
        print(f"High split MIF saved: {high_output_file}")

        # Optionally append content to mif_output for memory tracking
        if mif_output is not None:
            mif_output.extend([f"{line}" for line in low_content])
            mif_output.extend([f"{line}" for line in high_content])



#--------------------------------------------------checksum

def write_combined_binary(mif_low_output, mif_high_output, mif_16x32_output, output_file, target_size=81920):
    """
    Generates a binary file from MIF output, ensuring all addresses are sequentially filled,
    and writes in the order: 16x32 first, then 32x64 split (high first, then low).
    Appends a 16-bit checksum at the last 2 bytes.
    """
    import os

    debug_file_path = output_file.replace(".bin", "_debug.txt")

    # ----------------------------
    # Step 1: Load Data from the Correct MIF Files (Low, High, 16x32)
    # ----------------------------
    def load_mif_data(file_path):
        """Loads MIF content and returns a list of (address, data) tuples."""
        data = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if ":" in line and line.endswith(";"):
                    parts = line.split(":")
                    address_hex = parts[0].strip()
                    data_part = parts[1].split(";")[0].strip()
                    try:
                        address = int(address_hex, 16)
                        if len(data_part) == 4 and all(c in "0123456789ABCDEFabcdef" for c in data_part):
                            data.append((address, data_part))
                    except ValueError:
                        continue
        return data

    # Load MIF data from the correct files
    data_16x32 = load_mif_data(mif_16x32_output)
    data_32x64_high = load_mif_data(mif_high_output)
    data_32x64_low = load_mif_data(mif_low_output)

    # ----------------------------
    # Step 2: Print Parsed Data for Debugging
    # ----------------------------
    print("\n=== Debug: Parsed MIF Data ===")
    print("16x32 (First 20 lines):")
    for i, (addr, data) in enumerate(data_16x32[:20]):
        print(f"{i}: Addr {addr:04X} -> {data}")

    print("32x64 High (First 20 lines):")
    for i, (addr, data) in enumerate(data_32x64_high[:20]):
        print(f"{i}: Addr {addr:04X} -> {data}")

    print("32x64 Low (First 20 lines):")
    for i, (addr, data) in enumerate(data_32x64_low[:20]):
        print(f"{i}: Addr {addr:04X} -> {data}")

    print("=================================\n")

    # ----------------------------
    # Step 3: Write Debug Log
    # ----------------------------
    with open(debug_file_path, "w", encoding="utf-8") as debug_file:
        debug_file.write("DEBUG FILE FOR BINARY GENERATION\n\n")
        debug_file.write("\n### Parsed MIF Data ###\n")
        debug_file.write("\n16x32:\n" + "\n".join([f"{addr:04X} : {data}" for addr, data in data_16x32]))
        debug_file.write("\n32x64 High:\n" + "\n".join([f"{addr:04X} : {data}" for addr, data in data_32x64_high]))
        debug_file.write("\n32x64 Low:\n" + "\n".join([f"{addr:04X} : {data}" for addr, data in data_32x64_low]))

    # ----------------------------
    # Step 4: Write to Binary File
    # ----------------------------
    total_bytes_written = 0

    with open(output_file, "wb") as bin_file:
        print("\n=== Debug: Writing to Binary File ===")

        for address, data in data_16x32:
            bin_file.write(bytes.fromhex(data))
            total_bytes_written += 2

        for address, data in data_32x64_high:
            bin_file.write(bytes.fromhex(data))
            total_bytes_written += 2

        for address, data in data_32x64_low:
            bin_file.write(bytes.fromhex(data))
            total_bytes_written += 2

        while total_bytes_written < target_size - 2:
            bin_file.write(b"\x00\x00")
            total_bytes_written += 2

        print(f"Total Bytes Written (Before Checksum): {total_bytes_written}")

    print("Checking first 10 bytes in binary file...")
    with open(output_file, "rb") as f:
        first_10_bytes = f.read(100)
        print("First 10 Bytes (Hex):", first_10_bytes.hex())

    if total_bytes_written == 0 or first_10_bytes == b"\x00" * 10:
        print("No bytes were written! Data might not be parsed correctly.")

    # ----------------------------
    # Step 5: Compute and Append Checksum
    # ----------------------------
    def calculate_checksum(bin_path):
        checksum = 0
        with open(bin_path, "rb") as f:
            while True:
                chunk = f.read(2)
                if not chunk:
                    break
                if len(chunk) < 2:
                    chunk += b"\x00"
                word = int.from_bytes(chunk, "big")
                checksum = (checksum + word) & 0xFFFF
        return (~checksum) & 0xFFFF  # 1's complement

    checksum = calculate_checksum(output_file)
    with open(output_file, "ab") as bin_file:
        bin_file.write(checksum.to_bytes(2, "big"))

    # ----------------------------
    # Step 6: Append Checksum to Debug Log
    # ----------------------------
    with open(debug_file_path, "a", encoding="utf-8") as debug_file:
        debug_file.write(f"\n### Checksum ###\nChecksum (16-bit complement): 0x{checksum:04X}\n")

    print(f"Binary file saved: {output_file} ({total_bytes_written + 2} bytes written).")
    print(f"Checksum added: 0x{checksum:04X}")
    print(f"Debug log saved: {debug_file_path}")





#--------------------------------------------------




# def main():
#     ttf_path = r"c:\WINDOWS\Fonts\CAMBRIA.TTC"  # Path to font
#     char_list = (
#         [chr(i) for i in range(0x20, 0x61)] +  
#         [
#             chr(0x7B), chr(0x7C), chr(0x7D), chr(0x7E), chr(0xB0), chr(0xB1),
#             chr(0x2026),chr(0x2190), chr(0x2191), chr(0x2192), chr(0x2193),
#             chr(0x21CC), chr(0x25BC), chr(0x2713), chr(0x20)
#         ]
#     )

#     output_dir = r"C:\Users\theda\OneDrive\Desktop\out_test"  # Output directory

#     # Configuration
#     forced_height = 39
#     max_width = 17
#     canvas_width =32  # Canvas width in bits
#     canvas_height = 64  # Canvas height in rows
#     padding_top = 0
#     padding_bottom = 2


#     # # Configuration
#     # forced_height = 28
#     # max_width = 13
#     # canvas_width =16  # Canvas width in bits
#     # canvas_height = 32  # Canvas height in rows
#     # padding_top = 2
#     # padding_bottom = 2

 
#     # Generate data
#     os.makedirs(output_dir, exist_ok=True)
#     xbm_data = generate_xbm_data(ttf_path, char_list, forced_height, max_width, canvas_width, canvas_height,
#                                   padding_top=padding_top, padding_bottom=padding_bottom)

#     # Write XBM and MIF files
#     write_xbm(xbm_data, os.path.join(output_dir, f"FontRom{canvas_height}.xbm"), canvas_width, canvas_height)
#     write_mif(xbm_data, os.path.join(output_dir, f"FontRom{canvas_height}.mif"), canvas_width, canvas_height)


# if __name__ == "__main__":
#     main()


# GUI Functionality
def browse_ttf_path(entry):
    path = filedialog.askopenfilename(filetypes=[("Font Files", "*.ttf;*.ttc")])
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)

def browse_output_dir(entry):
    path = filedialog.askdirectory()
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)

def generate_files():
    try:
        # Get inputs
        ttf_path = ttf_entry.get()
        output_dir = output_dir_entry.get()
        
        forced_height_32x64 = int(forced_height_32x64_entry.get())
        max_width_32x64 = int(max_width_32x64_entry.get())
        padding_top_32x64 = int(padding_top_32x64_entry.get())
        padding_bottom_32x64 = int(padding_bottom_32x64_entry.get())

        forced_height_16x32 = int(forced_height_16x32_entry.get())
        max_width_16x32 = int(max_width_16x32_entry.get())
        padding_top_16x32 = int(padding_top_16x32_entry.get())
        padding_bottom_16x32 = int(padding_bottom_16x32_entry.get())

        # Validate paths
        if not os.path.exists(ttf_path):
            messagebox.showerror("Error", "Invalid TTF font path.")
            return
        if not os.path.exists(output_dir):
            messagebox.showerror("Error", "Invalid output directory path.")
            return

        # Character list
        char_list = (
            [chr(i) for i in range(0x20, 0x61)] +  
            [
                chr(0x7B), chr(0x7C), chr(0x7D), chr(0x7E), chr(0xB0), chr(0xB1),
                chr(0x2026), chr(0x2190), chr(0x2191), chr(0x2192), chr(0x2193),
                chr(0x21CC), chr(0x25BC), chr(0x2713), chr(0x20)
            ]
        )

        # Create output directory if not exists
        os.makedirs(output_dir, exist_ok=True)

        # Generate 32x64 files
        xbm_data_32x64 = generate_xbm_data(
            ttf_path, char_list, forced_height_32x64, max_width_32x64, 
            32, 64, padding_top=padding_top_32x64, padding_bottom=padding_bottom_32x64
        )
        write_xbm(xbm_data_32x64, os.path.join(output_dir, "FontRom64.xbm"), 32, 64)
        write_mif(xbm_data_32x64, os.path.join(output_dir, "FontRom64.mif"), 32, 64)

        # Generate 16x32 files
        xbm_data_16x32 = generate_xbm_data(
            ttf_path, char_list, forced_height_16x32, max_width_16x32, 
            16, 32, padding_top=padding_top_16x32, padding_bottom=padding_bottom_16x32
        )
        write_xbm(xbm_data_16x32, os.path.join(output_dir, "FontRom32.xbm"), 16, 32)
        write_mif(xbm_data_16x32, os.path.join(output_dir, "FontRom32.mif"), 16, 32)

        # Generate combined binary file (Use the CORRECT split MIF files)
        output_binary_file = os.path.join(output_dir, "FontRomCombined.bin")
        write_combined_binary(
            os.path.join(output_dir, "FontRom16x64_Low.mif"),
            os.path.join(output_dir, "FontRom16x64_High.mif"),
            os.path.join(output_dir, "FontRom32.mif"),
            output_binary_file
        )

        messagebox.showinfo("Success", "Files and combined binary generated successfully!")
    
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")


# GUI
root = tk.Tk()
root.title("Font to XBM/MIF Converter")

# TTF Path
ttf_label = tk.Label(root, text="TTF Font Path:")
ttf_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
ttf_entry = tk.Entry(root, width=50)
ttf_entry.grid(row=0, column=1, padx=5, pady=5)
ttf_browse = tk.Button(root, text="Browse", command=lambda: browse_ttf_path(ttf_entry))
ttf_browse.grid(row=0, column=2, padx=5, pady=5)

# Output Directory
output_dir_label = tk.Label(root, text="Output Directory:")
output_dir_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
output_dir_entry = tk.Entry(root, width=50)
output_dir_entry.grid(row=1, column=1, padx=5, pady=5)
output_dir_browse = tk.Button(root, text="Browse", command=lambda: browse_output_dir(output_dir_entry))
output_dir_browse.grid(row=1, column=2, padx=5, pady=5)

# 32x64 Configuration
config_32x64_label = tk.Label(root, text="32x64 Configuration:", font=("Arial", 12, "bold"))
config_32x64_label.grid(row=2, column=0, columnspan=3, pady=(10, 5))

forced_height_32x64_label = tk.Label(root, text="Forced Height:")
forced_height_32x64_label.grid(row=3, column=0, padx=5, pady=5, sticky="e")
forced_height_32x64_entry = tk.Entry(root)
forced_height_32x64_entry.insert(0, "39")
forced_height_32x64_entry.grid(row=3, column=1, padx=5, pady=5)

max_width_32x64_label = tk.Label(root, text="Max Width:")
max_width_32x64_label.grid(row=4, column=0, padx=5, pady=5, sticky="e")
max_width_32x64_entry = tk.Entry(root)
max_width_32x64_entry.insert(0, "17")
max_width_32x64_entry.grid(row=4, column=1, padx=5, pady=5)

padding_top_32x64_label = tk.Label(root, text="Padding Top:")
padding_top_32x64_label.grid(row=5, column=0, padx=5, pady=5, sticky="e")
padding_top_32x64_entry = tk.Entry(root)
padding_top_32x64_entry.insert(0, "0")
padding_top_32x64_entry.grid(row=5, column=1, padx=5, pady=5)

padding_bottom_32x64_label = tk.Label(root, text="Padding Bottom:")
padding_bottom_32x64_label.grid(row=6, column=0, padx=5, pady=5, sticky="e")
padding_bottom_32x64_entry = tk.Entry(root)
padding_bottom_32x64_entry.insert(0, "2")
padding_bottom_32x64_entry.grid(row=6, column=1, padx=5, pady=5)

# 16x32 Configuration
config_16x32_label = tk.Label(root, text="16x32 Configuration:", font=("Arial", 12, "bold"))
config_16x32_label.grid(row=7, column=0, columnspan=3, pady=(10, 5))

forced_height_16x32_label = tk.Label(root, text="Forced Height:")
forced_height_16x32_label.grid(row=8, column=0, padx=5, pady=5, sticky="e")
forced_height_16x32_entry = tk.Entry(root)
forced_height_16x32_entry.insert(0, "28")
forced_height_16x32_entry.grid(row=8, column=1, padx=5, pady=5)

max_width_16x32_label = tk.Label(root, text="Max Width:")
max_width_16x32_label.grid(row=9, column=0, padx=5, pady=5, sticky="e")
max_width_16x32_entry = tk.Entry(root)
max_width_16x32_entry.insert(0, "13")
max_width_16x32_entry.grid(row=9, column=1, padx=5, pady=5)

padding_top_16x32_label = tk.Label(root, text="Padding Top:")
padding_top_16x32_label.grid(row=10, column=0, padx=5, pady=5, sticky="e")
padding_top_16x32_entry = tk.Entry(root)
padding_top_16x32_entry.insert(0, "2")
padding_top_16x32_entry.grid(row=10, column=1, padx=5, pady=5)

padding_bottom_16x32_label = tk.Label(root, text="Padding Bottom:")
padding_bottom_16x32_label.grid(row=11, column=0, padx=5, pady=5, sticky="e")
padding_bottom_16x32_entry = tk.Entry(root)
padding_bottom_16x32_entry.insert(0, "2")
padding_bottom_16x32_entry.grid(row=11, column=1, padx=5, pady=5)

# Generate Button
generate_button = tk.Button(root, text="Generate Files", command=generate_files)
generate_button.grid(row=12, column=0, columnspan=3, pady=10)

root.mainloop()
