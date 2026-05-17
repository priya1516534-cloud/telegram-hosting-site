def extract_list_from_file(file_storage):
    try:
        raw_data = file_storage.read()
        decoded_text = raw_data.decode('utf-8', errors='ignore')
        parsed_list = [line.strip() for line in decoded_text.splitlines() if line.strip()]
        return parsed_list
    except:
        return []
