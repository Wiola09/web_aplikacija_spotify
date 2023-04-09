import requests
from bs4 import BeautifulSoup


class Top100Movies:

    def lista_top_100_pesama(self, godina):
        def formiraj_url():
            # datum = input("what year you would like to travel to in YYYY-MM-DD format")
            datum = f"{godina}"
            print(datum)
            url = f"https://www.billboard.com/charts/hot-100/{datum}"
            print(url)
            # 2000-08-12
            return url

        url = formiraj_url()

        def formiraj_supu_i_izbaci_sirov_tekst(url):
            response = requests.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            # print(soup.prettify())
            klasa = "c-title"
            # pesma = soup.find(name="h3", class_=klasa).getText().strip()
            pesme_lista_sirovo = soup.find_all(name="h3", class_=klasa, id="title-of-a-story")
            print(len(pesme_lista_sirovo))
            return pesme_lista_sirovo

        pesme_lista_sirovo = formiraj_supu_i_izbaci_sirov_tekst(url)

        # print(pesme_lista_sirovo)
        def podaci_bez_razmaka():
            for i in pesme_lista_sirovo:
                tekst = i.getText().strip()
                if tekst != "":
                    print(tekst)
                    print(60 * "+")

        pesme_lista = []
        for i in pesme_lista_sirovo:
            pesme_lista.append(i.getText().strip())

        for indeks, element in enumerate(pesme_lista[:8]):
            # print(indeks, element)
            if element == "Additional Awards":
                pocetni_ideks_pesma = indeks + 1
                print(pocetni_ideks_pesma)

        pesme_lista_100 = [pesme_lista[i] for i in range(pocetni_ideks_pesma, 404, 4)]
        print(len(pesme_lista_100))
        return pesme_lista_100