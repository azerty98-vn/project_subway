import mimetypes
import os
import psycopg2
import json
import sys
from os.path import expanduser

import pandas as pd
import requests
from PyQt5 import QtWidgets

# import folium, io, json, sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMainWindow, QApplication, QComboBox, QPushButton, QLabel, QHBoxLayout, QVBoxLayout, \
    QWidget, QCompleter
from sqlalchemy import create_engine

os.chdir(sys.path[0])
sys.path.append('../modules')

import params
import route_type

# See params.py
data_path, user, password, database, host = params.get_variables()
sys.path.append(data_path)
dp = expanduser(data_path)
number_of_click = 0

conn = psycopg2.connect(database=str(database), user=str(user), host=str(host), password=str(password))
cursor = conn.cursor()
print("database project connected to server")
engine = create_engine(
    'postgresql+psycopg2://' + str(user) + ':' + str(password) + '@' + str(host) + '/' + str(database))

if not os.path.isdir('./data_json'):
    os.makedirs('./data_json')

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.route = None
        self.route_type = None
        self.route_name = None
        self.resize(600, 600)

        self.main = QWidget()
        self.setCentralWidget(self.main)
        self.main.setLayout(QVBoxLayout())
        self.main.setFocusPolicy(Qt.StrongFocus)

        self.label = QLabel(self)
        self.pixmap = QPixmap('Scrape/BUS 180 Paris.jpg')
        self.label.setPixmap(self.pixmap)

        controls_panel = QHBoxLayout()
        self.main.layout().addLayout(controls_panel)
        self.main.layout().addWidget(self.label)

        # _label.setFixedSize(30,20)
        self.route_box = QComboBox()
        self.route_box.setEditable(True)
        self.route_box.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.route_box.setInsertPolicy(QComboBox.NoInsert)
        controls_panel.addWidget(self.route_box, stretch=1)

        self.go_button = QPushButton("Go!")
        self.go_button.clicked.connect(self.button_Go)
        controls_panel.addWidget(self.go_button, stretch=1)

        self.connect_DB()
        self.show()

    def connect_DB(self):

        # We only redo everything if the table is yet to be filled
        cursor.execute(f"SELECT * FROM information_schema.tables WHERE table_name='lines'")
        if cursor.rowcount <= 0:

            # Open the json file that tells the line names related to their line IDs

            # File source: https://data.iledefrance-mobilites.fr/explore/dataset/referentiel-des-lignes
            with open('referentiel-des-lignes.json', 'r') as f:
                json_file = json.load(f)
            data = [[line['fields']['transportmode'], line['fields']['id_line'], line['fields']['name_line']] for line
                    in
                    json_file]
            lines = pd.DataFrame(data, columns=['transportmode', 'id_line', 'name_line'])

            # Open the json file that gives the url relative to a line_id

            # File source: https://data.iledefrance-mobilites.fr/explore/dataset/fiches-horaires-et-plans/
            with open('fiches-horaires-et-plans.json', 'r') as f:
                json_file = json.load(f)
            data = [[line['fields']['id_line'], line['fields']['url']] for line in json_file]
            urls = pd.DataFrame(data, columns=['id_line', 'url'])

            # Merge the results of the two json files above, then add it to the database
            merge = pd.merge(lines, urls, how='inner', on=["id_line"])
            merge = merge.drop_duplicates()
            route_merge = merge['transportmode'].values

            # Convert transportmode to route_type before moving on
            for i in range(len(route_merge)):
                route_merge[i] = int(route_type.str_route_num(route_merge[i]))
            merge['transportmode'] = route_merge
            merge = merge.rename(columns={'transportmode': 'route_type'})
            merge.to_sql('lines', con=engine, if_exists='replace', index=False)

            cursor.execute("""ALTER TABLE lines
            ADD PRIMARY KEY (url, id_line)""")
            conn.commit()

        cursor.execute("""SELECT distinct route_type,route_name FROM routes ORDER BY route_type DESC""")
        conn.commit()
        rows = cursor.fetchall()
        for row in rows:
            self.route_box.addItem(route_type.str_route_type(row[0]) + ' ' + row[1])

    def button_Go(self):
        self.route = str(self.route_box.currentText())
        if os.path.exists(os.path.join('./data_json/', self.route)):
            self.pixmap = QPixmap(os.path.join('./data_json/', self.route),
                                  '1')  # .scaled(self.label.width(), self.label.height(), Qt.KeepAspectRatio)
            self.label.setPixmap(self.pixmap)
            return
        self.route_type = int(route_type.str_route_num(self.route.split(' ')[0]))
        self.route_name = self.route.split(' ')[1]
        # Code to downnload the pdf/jpeg file from the url indicated in the database, then display it
        cursor.execute(f""" SELECT id_line, url FROM lines WHERE name_line = '{self.route_name}' and route_type = {self.route_type}""")
        conn.commit()
        myrows = cursor.fetchall()
        if len(myrows) <= 0:
            err = QtWidgets.QMessageBox()
            err.setIcon(QtWidgets.QMessageBox.Warning)
            err.setText(f"pas d'URL spécifiée pour la ligne {self.route}")
            err.exec_()
            self.pixmap = QPixmap(os.path.join('.', 'default.png'))
            self.label.setPixmap(self.pixmap)
            return

        for row in myrows:
            print(row)
            file_name = row[0]
            file_url = row[1]
            try:
                response = requests.get(file_url)
                extension = mimetypes.guess_extension(response.headers['content-type'])
                if (extension is not None) and (response.headers['content-type'] != 'text/html'):
                    file_name = file_name + extension
                    if not os.path.exists(os.path.join('./data_json/', file_name)):
                        print(f"{file_name} : {response.headers['content-type']}")

                        with open(os.path.join('./data_json/', file_name), 'wb') as f:
                            f.write(response.content)
                            return
                    else:
                        print(f"{file_name} existe déjà")
                        return
                else:
                    print(f"le fichier à l'adresse {file_url} n'est ni un pdf, ni une image!")
                    # Insert beautifulsoup html handling
            except requests.exceptions.ConnectionError:
                print(f'Timeout à l\'adresse {file_url}')
        print("La ligne a été traitée")
        return


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
