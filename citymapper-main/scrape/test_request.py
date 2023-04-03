import requests

URL = "https://www.datocms-assets.com/56495/1633687973-fileovillierslebel.pdf"

# Envoi d'une requête GET pour récupérer le fichier PDF
response = requests.get(URL)

# Vérification du code de statut de la réponse
if response.status_code == 200:
  # Si le téléchargement a réussi, écriture du fichier sur le disque
  with open("fileovillierslebel.pdf", "wb") as f:
    f.write(response.content)
    print("Le fichier a été téléchargé avec succès.")
else:
  # Si le téléchargement a échoué, affichage d'un message d'erreur
  print(f"Erreur lors du téléchargement du fichier: code de statut {response.status_code}")
