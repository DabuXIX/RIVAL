def write_combined_binary(mif_low_file, mif_high_file, mif_16x32_file, output_file, target_size=81920):
    """
    Generates a binary file from split MIF files with fixed section offsets:
      - 16x32 section at offset 0x0000 (16K region)
      - 32x64 High section at offset 0x4000 (32K region)
      - 32x64 Low section at offset 0xC000 (32K region)
    
    The binary file will include a 16-bit checksum, so the data area is pre-padded to
    (target_size - 2) bytes and then the checksum (2 bytes) is appended, making the total size target_size.
    """
    import os

    # We want the final file to be target_size bytes including the 2-byte checksum.
    prefill_size = target_size - 2

    # Define base offsets for each section.
    base_offsets = {
        "16x32": 0x0000,         # 16K region: 0x0000 to 0x3FFF
        "32x64 High": 0x4000,    # 32K region: 0x4000 to 0xBFFF
        "32x64 Low": 0xC000      # 32K region: 0xC000 to 0x13FFF
    }

    # Helper: load MIF data from a file into a list of (address, data_str) tuples.
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
                # Expect a 16-bit word (4 hex digits)
                if len(data_str) == 4 and all(c in "0123456789ABCDEFabcdef" for c in data_str):
                    entries.append((addr, data_str))
        return entries

    # Load data from each split MIF file.
    data_32x64_low = load_mif_data(mif_low_file)
    data_32x64_high = load_mif_data(mif_high_file)
    data_16x32 = load_mif_data(mif_16x32_file)

    # For the 16x32 section, remap addresses so that the lowest address is 0 (if needed).
    if data_16x32:
        base_addr = min(addr for addr, _ in data_16x32)
        if base_addr != 0:
            data_16x32 = [(addr - base_addr, d) for addr, d in data_16x32]

    # Pre-fill the output file with zeros up to prefill_size bytes.
    with open(output_file, "wb") as bin_file:
        bin_file.write(b"\x00" * prefill_size)

    # Open the file in r+b mode for random-access writing.
    with open(output_file, "r+b") as bin_file:
        # Write the 16x32 section at offset 0x0000.
        for addr, d in data_16x32:
            offset = base_offsets["16x32"] + (addr * 2)
            if offset < prefill_size:
                bin_file.seek(offset)
                bin_file.write(bytes.fromhex(d))
        # Write the 32x64 High section at offset 0x4000.
        for addr, d in data_32x64_high:
            offset = base_offsets["32x64 High"] + (addr * 2)
            if offset < prefill_size:
                bin_file.seek(offset)
                bin_file.write(bytes.fromhex(d))
        # Write the 32x64 Low section at offset 0xC000.
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
    # Append the checksum (2 bytes) to the file.
    with open(output_file, "ab") as bin_file:
        bin_file.write(checksum.to_bytes(2, "big"))

    print("✅ Combined binary written to", output_file)
    print("Total file size:", os.path.getsize(output_file), "bytes")
    print("Checksum appended: 0x{:04X}".format(checksum))
