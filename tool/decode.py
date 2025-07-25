import base64
import gzip
import json
import os
from datetime import datetime

def decode_bdengine_file(file_path):
    """Décode un fichier .bdengine"""
    try:
        # Lire le contenu du fichier
        with open(file_path, 'r') as file:
            encoded_content = file.read().strip()
        
        # Étape 1: Décoder Base64
        print("Décodage Base64...")
        compressed_data = base64.b64decode(encoded_content)
        
        # Étape 2: Décompresser avec gzip
        print("Décompression gzip...")
        decompressed_data = gzip.decompress(compressed_data)
        
        # Étape 3: Décoder en UTF-8
        decoded_text = decompressed_data.decode('utf-8')
        
        # Étape 4: Essayer de parser en JSON si possible
        try:
            json_data = json.loads(decoded_text)
            return json_data, "json"
        except json.JSONDecodeError:
            return decoded_text, "text"
            
    except Exception as e:
        print(f"Erreur lors du décodage: {e}")
        return None, None

def save_decoded_data(data, data_type, original_file_path):
    """Sauvegarde les données décodées dans un dossier organisé"""
    # Créer le dossier de sortie
    output_dir = "decoded_bdengine"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Nom de base du fichier original
    base_name = os.path.splitext(os.path.basename(original_file_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if data_type == "json":
        # Si c'est déjà du JSON, sauvegarder directement
        output_file = os.path.join(output_dir, f"{base_name}_{timestamp}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Données JSON sauvegardées dans: {output_file}")
        
    else:
        # Si c'est du texte, essayer de le structurer en JSON
        json_output = {
            "metadata": {
                "original_file": original_file_path,
                "decoded_at": datetime.now().isoformat(),
                "data_type": "text"
            },
            "content": data
        }
        
        output_file = os.path.join(output_dir, f"{base_name}_{timestamp}_text.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_output, f, indent=2, ensure_ascii=False)
        print(f"Données texte sauvegardées en JSON dans: {output_file}")
    
    return output_file

file_path = "color_block_rot.bdengine"
result, data_type = decode_bdengine_file(file_path)

if result:
    print(f"Type de données: {data_type}")
    
    # Sauvegarder dans un fichier JSON
    output_file = save_decoded_data(result, data_type, file_path)
    
    # Afficher un aperçu du contenu
    print("\nAperçu du contenu décodé:")
    if data_type == "json":
        preview = json.dumps(result, indent=2, ensure_ascii=False)
        print(preview[:500] + "..." if len(preview) > 500 else preview)
    else:
        print(result[:500] + "..." if len(result) > 500 else result)
        
else:
    print("Échec du décodage")