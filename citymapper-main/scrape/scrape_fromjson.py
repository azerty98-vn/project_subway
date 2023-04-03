import json
import requests
import os
import sys
import mimetypes

os.chdir(sys.path[0])


if not os.path.isdir('./data_json'):
    os.makedirs('./data_json')

# Chargez le JSON à partir de un fichier
with open('fiches-horaires-et-plans.json', 'r') as f:
    data = json.load(f)

# Pour chaque élément de "data"
for item in data:
    file_url = item['fields']['url']
    file_name = item['fields']['id_line']

    try:
        response = requests.get(file_url)
        extension = mimetypes.guess_extension(response.headers['content-type'])
        if (extension is not None) and (response.headers['content-type'] != 'text/html'):
            file_name = file_name + extension
            if not os.path.exists(os.path.join('./data_json/', file_name)):
                print(f"{file_name} : {response.headers['content-type']}")

                with open(os.path.join('./data_json/', file_name), 'wb') as f:
                    f.write(response.content)
            else:
                print(f"{file_name} existe déjà")
        else:
            print(f"le fichier à l'adresse {file_url} n'est ni un pdf, ni une image!")
    except requests.exceptions.ConnectionError:
        print(f'Timeout à l\'adresse {file_url}')

print("Téléchargement terminé !")