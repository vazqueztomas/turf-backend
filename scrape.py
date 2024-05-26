import requests
from bs4 import BeautifulSoup

# URL of the page to scrape
url = "https://www.palermo.com.ar/es/turf/programa-oficial"

# Send a GET request to the page
response = requests.get(url)


# Check if the request was successful
if response.status_code == 200:
    # Parse the page content
    soup = BeautifulSoup(response.content, "html.parser")

    # Find all article titles (assuming they are within <h2> tags with class 'post-title')
    divs = soup.find_all("td", class_="tabla_hora")

    # Extract and print the text of each title
    for div in divs:
        print("title: ", div.get_text())
else:
    print(f"Failed to retrieve the page. Status code: {response.status_code}")
