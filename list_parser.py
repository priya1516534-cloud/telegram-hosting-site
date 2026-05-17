def extract_list_from_file(file_storage):
    """File ke andar ke data ko read karke lines ko alag karne ka core system"""
    try:
        # File ka raw content read karna
        raw_data = file_storage.read()
        
        # Binary ko text mein decode karna
        decoded_text = raw_data.decode('utf-8', errors='ignore')
        
        # Har ek line ko alag list element banana (Khali lines ko hatana)
        parsed_list = [line.strip() for line in decoded_text.splitlines() if line.strip()]
        
        print(f"⚙️ [PARSER SUCCESS] Total extracted items: {len(parsed_list)}")
        return parsed_list
    except Exception as e:
        print(f"❌ [PARSER ERROR] Error extracting list data: {e}")
        return []
      
