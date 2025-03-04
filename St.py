def write_combined_binary(mif_low_file, mif_high_file, mif_16x32_file, output_file, target_size=81920):
    """
    Generates a combined binary file from split MIF files.
    
    Expected parameter order:
      - mif_low_file:  MIF for 32x64 Low section (written at offset 0xC000)
      - mif_high_file: MIF for 32x64 High section (written at offset 0x4000)
      - mif_16x32_file: MIF for 16x32 section (which contains both normal and strikeout characters)
         The 16x32 MIF file is parsed so that the strikeout characters (which normally start at 0x2000)
         are remapped to immediately follow the normal characters.
         
    The binary file is pre-padded to (target_size - 2) bytes, then a 16-bit checksum (1's complement)
    is appended so that the total file size is exactly target_size bytes.
    """
    import os

    # We want the data area (without the checksum) to be target_size - 2 bytes.
    prefill_size = target_size - 2

    # Define base offsets (in bytes) for each section.
    # 16x32: occupies the first 16K bytes (0x0000 to 0x3FFF)
    # 32x64 High: occupies the next 32K bytes (0x4000 to 0xBFFF)
    # 32x64 Low: occupies the final 32K bytes (0xC000 to 0x13FFF)
    base_offsets = {
        "16x32": 0x0000,
        "32x64 High": 0x4000,
        "32x64 Low": 0xC000
    }

    # Standard MIF loader for the 32x64 files.
    def load_mif_data(file_path):
        entries = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
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

    # Custom loader for the 16x32 MIF file.
    # It assumes that the file contains a normal section first, then a strikeout section
    # (indicated by a line containing "strikeout").
    # Normal entries are assigned addresses starting at 0.
    # Strikeout entries are remapped to immediately follow the normal ones.
    def load_mif_data_16x32(file_path):
        entries = []
        mode = "normal"       # initial mode is normal characters
        normal_count = 0      # count how many normal words we have
        strikeout_index = 0   # counter for strikeout entries
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("--"):
                    # When we see a comment that mentions "strikeout", switch mode.
                    if "strikeout" in line.lower():
                        mode = "strikeout"
                    continue
                if ":" not in line or not line.endswith(";"):
                    continue
                parts = line.split(":")
                # We ignore the address in the file and use our own counters.
                data_str = parts[1].split(";")[0].strip()
                if len(data_str) == 4 and all(c in "0123456789ABCDEFabcdef" for c in data_str):
                    if mode == "normal":
                        entries.append((normal_count, data_str))
                        normal_count += 1
                    else:  # strikeout mode: remap address to follow normal entries
                        entries.append((normal_count + strikeout_index, data_str))
                        strikeout_index += 1
        return entries

    # Load the three sections.
    data_32x64_low = load_mif_data(mif_low_file)
    data_32x64_high = load_mif_data(mif_high_file)
    data_16x32 = load_mif_data_16x32(mif_16x32_file)

    # Debug prints
    print("16x32 entries (normal+strikeout):", len(data_16x32))
    print("32x64 High entries:", len(data_32x64_high))
    print("32x64 Low entries:", len(data_32x64_low))

    # Pre-fill the output file with zeros up to prefill_size bytes.
    with open(output_file, "wb") as bin_file:
        bin_file.write(b"\x00" * prefill_size)

    # Write the data at fixed offsets.
    with open(output_file, "r+b") as bin_file:
        # Write 16x32 section (both normal and strikeout remapped) at offset 0x0000.
        for addr, d in data_16x32:
            offset = base_offsets["16x32"] + (addr * 2)
            if offset < prefill_size:
                bin_file.seek(offset)
                bin_file.write(bytes.fromhex(d))
        # Write 32x64 High section at offset 0x4000.
        for addr, d in data_32x64_high:
            offset = base_offsets["32x64 High"] + (addr * 2)
            if offset < prefill_size:
                bin_file.seek(offset)
                bin_file.write(bytes.fromhex(d))
        # Write 32x64 Low section at offset 0xC000.
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
