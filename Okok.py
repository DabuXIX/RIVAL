def write_combined_binary(mif_low_file, mif_high_file, mif_16x32_file, output_file, target_size=81920):
    """
    Generates a combined binary file from split MIF files.

    Parameter order:
      - mif_low_file:  MIF for 32x64 Low section (written at offset 0xC000)
      - mif_high_file: MIF for 32x64 High section (written at offset 0x4000)
      - mif_16x32_file: MIF for 16x32 section which contains both normal and strikeout characters.
         In this MIF file, normal characters have addresses starting at 0000,
         and strikeout characters appear with addresses (as written) but we want them
         to be written starting at binary offset 0x2000.
    
    The function pre-fills the binary file to (target_size - 2) bytes, writes all sections at fixed offsets,
    then computes and appends a 2-byte checksum so the total file size is exactly target_size.
    """
    import os

    # We want the data area (without the checksum) to be target_size - 2 bytes.
    prefill_size = target_size - 2

    # Base offsets for the fixed sections (in bytes):
    # - 16x32: normal data will be written at 0x0000.
    # - For 16x32 strikeout, we force the start at 0x2000.
    # - 32x64 High: starts at 0x4000.
    # - 32x64 Low: starts at 0xC000.
    base_offsets = {
        "32x64 High": 0x4000,
        "32x64 Low": 0xC000
    }

    # Standard MIF loader (for 32x64 sections).
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
    # It distinguishes normal characters from strikeout characters based on a comment.
    # Normal entries are assigned an index starting at 0.
    # Once a comment containing "strikeout" is encountered, subsequent entries are considered strikeout,
    # and they will be written starting at binary offset 0x2000.
    def load_mif_data_16x32(file_path):
        entries = []
        mode = "normal"       # initial mode is normal
        normal_count = 0      # counter for normal entries
        strikeout_count = 0   # counter for strikeout entries
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("--"):
                    if "strikeout" in line.lower():
                        mode = "strikeout"
                    continue
                if ":" not in line or not line.endswith(";"):
                    continue
                parts = line.split(":")
                data_str = parts[1].split(";")[0].strip()
                if len(data_str) == 4 and all(c in "0123456789ABCDEFabcdef" for c in data_str):
                    if mode == "normal":
                        entries.append(("normal", normal_count, data_str))
                        normal_count += 1
                    else:
                        entries.append(("strikeout", strikeout_count, data_str))
                        strikeout_count += 1
        return entries

    # Load the data from the three MIF files.
    data_32x64_low = load_mif_data(mif_low_file)
    data_32x64_high = load_mif_data(mif_high_file)
    data_16x32 = load_mif_data_16x32(mif_16x32_file)

    # Debug prints: show the number of entries loaded.
    print("16x32 entries:", len(data_16x32))
    print("32x64 High entries:", len(data_32x64_high))
    print("32x64 Low entries:", len(data_32x64_low))

    # Pre-fill the output file with zeros for prefill_size bytes.
    with open(output_file, "wb") as bin_file:
        bin_file.write(b"\x00" * prefill_size)

    # Open the binary file for random-access writing.
    with open(output_file, "r+b") as bin_file:
        # Write the 16x32 section.
        for mode, index, d in data_16x32:
            if mode == "normal":
                offset = 0x0000 + (index * 2)
            else:  # strikeout mode: force start at binary offset 0x2000
                offset = 0x2000 + (index * 2)
            if offset < prefill_size:
                bin_file.seek(offset)
                bin_file.write(bytes.fromhex(d))
        # Write the 32x64 High section.
        for addr, d in data_32x64_high:
            offset = base_offsets["32x64 High"] + (addr * 2)
            if offset < prefill_size:
                bin_file.seek(offset)
                bin_file.write(bytes.fromhex(d))
        # Write the 32x64 Low section.
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
    # Append the checksum (2 bytes) so that the total file size becomes target_size.
    with open(output_file, "ab") as bin_file:
        bin_file.write(checksum.to_bytes(2, "big"))

    print("✅ Combined binary written to", output_file)
    print("Total file size:", os.path.getsize(output_file), "bytes")
    print("Checksum appended: 0x{:04X}".format(checksum))
