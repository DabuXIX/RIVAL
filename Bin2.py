def write_combined_binary(mif_low_file, mif_high_file, mif_16x32_file, output_file, target_size=81920):
    """
    Generates a combined binary file from split MIF files.
    
    Parameter order:
      - mif_low_file:  MIF for the 32x64 Low section (written at offset 0xC000)
      - mif_high_file: MIF for the 32x64 High section (written at offset 0x4000)
      - mif_16x32_file: MIF for the 16x32 section. This file contains both normal and strikeout characters.
                        In this file, normal entries have addresses starting at 0x0000 and
                        strikeout entries start at 0x2000.
                        In the binary, normal characters will be written at offset 0x0000,
                        and strikeout characters will be written beginning at offset 0x2000.
      
    The binary file is pre-padded to (target_size - 2) bytes, and then a 16-bit checksum is appended so that the total size is target_size.
    """
    import os

    # We want the final data area (without checksum) to be target_size - 2 bytes.
    prefill_size = target_size - 2

    # Define base offsets (in bytes) for each section:
    # For 16x32, we will handle mapping specially.
    # For 32x64 High: data goes from offset 0x4000.
    # For 32x64 Low: data goes from offset 0xC000.
    base_offsets = {
        "32x64 High": 0x4000,
        "32x64 Low": 0xC000
    }

    # Standard helper: load MIF data from a file into a list of (address, data_str) tuples.
    def load_mif_data(file_path):
        entries = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Process lines like "XXXX : YYYY;"
                if ":" not in line or not line.endswith(";"):
                    continue
                parts = line.split(":")
                address_str = parts[0].strip()
                data_str = parts[1].split(";")[0].strip()
                try:
                    addr = int(address_str, 16)
                except ValueError:
                    continue
                if len(data_str) == 4 and all(c in "0123456789ABCDEFabcdef" for c in data_str):
                    entries.append((addr, data_str))
        return entries

    # Load data from each MIF file.
    data_32x64_low = load_mif_data(mif_low_file)
    data_32x64_high = load_mif_data(mif_high_file)
    data_16x32 = load_mif_data(mif_16x32_file)  # Do not remap these; we want to preserve strikeout addresses

    # Debug prints: count entries
    print("16x32 entries:", len(data_16x32))
    print("32x64 High entries:", len(data_32x64_high))
    print("32x64 Low entries:", len(data_32x64_low))

    # Pre-fill the output file with zeros up to prefill_size bytes.
    with open(output_file, "wb") as bin_file:
        bin_file.write(b"\x00" * prefill_size)

    # Open the file in r+b mode for random-access writing.
    with open(output_file, "r+b") as bin_file:
        # --- Write the 16x32 section ---
        # For the 16x32 MIF file, we want:
        #   - Normal characters (addr < 0x2000) to be written at offset = (addr * 2)
        #   - Strikeout characters (addr >= 0x2000) to be written starting at offset 0x2000,
        #     i.e. offset = 0x2000 + ((addr - 0x2000) * 2)
        for addr, d in data_16x32:
            if addr < 0x2000:
                offset = (addr * 2)
            else:
                offset = 0x2000 + ((addr - 0x2000) * 2)
            if offset < prefill_size:
                bin_file.seek(offset)
                bin_file.write(bytes.fromhex(d))
        
        # --- Write the 32x64 High section ---
        for addr, d in data_32x64_high:
            offset = base_offsets["32x64 High"] + (addr * 2)
            if offset < prefill_size:
                bin_file.seek(offset)
                bin_file.write(bytes.fromhex(d))
        
        # --- Write the 32x64 Low section ---
        for addr, d in data_32x64_low:
            offset = base_offsets["32x64 Low"] + (addr * 2)
            if offset < prefill_size:
                bin_file.seek(offset)
                bin_file.write(bytes.fromhex(d))

    # Compute the 16-bit checksum over the first prefill_size bytes.
    def calculate_checksum(bin_path):
        checksum = 0
        with open(bin_path, "rb") as f:
            data = f.read(prefill_size)
            for i in range(0, len(data), 2):
                word = int.from_bytes(data[i:i+2], "big")
                checksum = (checksum + word) & 0xFFFF
        return (~checksum) & 0xFFFF  # 1's complement

    checksum = calculate_checksum(output_file)
    # Append the checksum (2 bytes) so the total file size becomes target_size.
    with open(output_file, "ab") as bin_file:
        bin_file.write(checksum.to_bytes(2, "big"))

    print("✅ Combined binary written to", output_file)
    print("Total file size:", os.path.getsize(output_file), "bytes")
    print("Checksum appended: 0x{:04X}".format(checksum))
