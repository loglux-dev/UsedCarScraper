import requests
from lxml import html
import csv
from bs4 import BeautifulSoup
import re  # Import the regular expressions library

class CarScraper:
    def __init__(self, url, file_name="cars"):
        self.url = url
        self.file_name = file_name
        self.base_url = "https://www.usedcarsni.com"
        self.page_number = "&pagepc0="
        self.car_catalogue = []
        self.session = requests.Session()
        self.session.headers.update(
            {'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0)'})

    def start(self):
        page_scope = self.get_total_pages()
        if page_scope > 0:
            self.known_makes = self.extract_known_makes()  # Extract known makes dynamically
            self.scrape_directory(page_scope)
        else:
            print("No pages to scrape. Check the URL or website structure.")

    def get_total_pages(self):
        response = self.session.get(self.url)
        if response.status_code != 200:
            print(f"Failed to connect, status code: {response.status_code}")
            return 0

        tree = html.fromstring(response.text)
        page_scope = tree.xpath("//div[@class='page-control-label']/text()")
        if page_scope:
            page_scope = page_scope[0].strip()
            page_total = int(page_scope.split()[-1])
            return page_total // 20 + (1 if page_total % 20 else 0)

        print("No page scope found.")
        return 0

    def extract_known_makes(self):
        """
        Extracts known car makes from the select options in the page.
        """
        response = self.session.get(self.url)
        if response.status_code != 200:
            print("Failed to retrieve makes, continuing with default list")
            return []

        tree = html.fromstring(response.content)
        # Extract options under the 'Make' dropdown
        options = tree.xpath("//select[@name='make']/option/text()")
        # Create a list of known makes
        makes = [option.split('(')[0].strip() for option in options if '(' in option]
        print(f"Extracted known makes: {makes}")
        return makes

    def scrape_directory(self, page_scope):
        for x in range(1, page_scope + 1):
            page_url = f"{self.url}{self.page_number}{x}"
            print(f"Scraping page: {x} URL: {page_url}")
            self.scrape_page(page_url)

    def scrape_page(self, page_url):
        response = self.session.get(page_url)
        if response.status_code != 200:
            print(
                f"Failed to retrieve page: {page_url}, Status Code: {response.status_code}")
            return

        tree = html.fromstring(response.content)
        car_elements = tree.xpath(
            "//article[contains(@class, 'car-line')]")
        print(f"Found {len(car_elements)} car elements on page: {page_url}")

        if not car_elements:
            print(f"No car elements found on page: {page_url}")
            return

        for car_elem in car_elements:
            self.parse_car_data(car_elem)

    def parse_car_data(self, car_elem):
        try:
            car_url = car_elem.xpath(".//a/@href")[0]
            car_url = self.base_url + car_url
            print(f"Found car URL: {car_url}")

            # Extract car details from the car detail page instead
            car_details = self.scrape_car_details(car_url)

            # Extract car year from the details
            car_year = car_details.get('Year', 'N/A')

            # Extract car make and model from details
            car_make = car_details.get('Make', 'Make not found')
            car_model = car_details.get('Model', 'Model not found')

            print(f"Make: {car_make}, Model: {car_model}, Year: {car_year}")

        except IndexError as e:
            print(f"Error extracting car details: {e}")
            return

        try:
            car_price_text = car_elem.xpath(
                ".//div[contains(@class, 'car-price-right-block')]//strong/text()")
            car_price = car_price_text[0].strip().replace(
                '£', '').replace(',', '') if car_price_text else 'Price not found'
        except IndexError:
            car_price = 'Price not found'
        print(f"Price: {car_price}")

        try:
            car_mileage_text = car_elem.xpath(
                ".//div[@class='options-small' and contains(text(), 'miles')]/text()")
            # Extract only the numeric part using regex
            car_mileage = re.search(
                r'\d+', car_mileage_text[0]).group() if car_mileage_text else 'Mileage not found'
        except (IndexError, AttributeError):
            car_mileage = 'Mileage not found'
        print(f"Mileage: {car_mileage}")

        car_engine_size = car_details.get(
            'Engine Size', 'Engine size not found')
        car_fuel_type = car_details.get('Fuel Type', 'Fuel type not found')
        car_transmission = car_details.get(
            'Transmission', 'Transmission not found')
        car_body_style = car_details.get(
            'Body Style', 'Body style not found')
        car_location = car_details.get('Location', 'Location not found')
        car_standard_tax = car_details.get(
            'Standard Tax', 'Standard Tax not found')
        car_insurance = car_details.get('Insurance', 'Insurance not found')
        print(
            f"Engine size: {car_engine_size}, Fuel type: {car_fuel_type}, Transmission: {car_transmission}, Body style: {car_body_style}, Location: {car_location}, Standard Tax: {car_standard_tax}, Insurance: {car_insurance}")

        car_description = {
            'Make': car_make,
            'Model': car_model,
            'Year': car_year,
            'Price': car_price,
            'Mileage': car_mileage,
            'Engine': car_engine_size,
            'Fuel': car_fuel_type,
            'Transmission': car_transmission,
            'Body Style': car_body_style,
            'Location': car_location,
            'Standard Tax': car_standard_tax,
            'Insurance': car_insurance,
            'Link': car_url
        }

        # Ensure at least Make and Model are valid to consider a successful parse
        if car_description['Make'] != 'Make not found' and car_description['Model'] != 'Model not found':
            self.car_catalogue.append(car_description)
            print(car_description)

    def scrape_car_details(self, car_url):
        response = self.session.get(car_url)
        if response.status_code != 200:
            print(
                f"Failed to retrieve car detail page: {car_url}, Status Code: {response.status_code}")
            return {}

        soup = BeautifulSoup(response.content, 'html.parser')

        # Scraping the specifications from the technical parameters
        specs = {}
        try:
            # Find the technical parameters section
            tech_params = soup.find('div', class_='technical-params')
            if tech_params:
                rows = tech_params.find_all(
                    'div', class_='row', role='listitem')
                for row in rows:
                    header_div = row.find('div', class_='technical-headers')
                    info_div = row.find('div', class_='technical-info')

                    if header_div and info_div:
                        header = header_div.get_text(strip=True)  # Remove extra spaces
                        info = info_div.get_text(strip=True)

                        # Specifically extract Engine Size, Transmission, Fuel Type, Body Style, Location, Standard Tax, and Insurance
                        if header == "Engine Size":
                            specs["Engine Size"] = info
                        elif header == "Transmission":
                            specs["Transmission"] = info
                        elif header == "Fuel Type":
                            specs["Fuel Type"] = info
                        elif header == "Body Style":
                            specs["Body Style"] = info
                        elif header == "Location":
                            specs["Location"] = info
                        elif header == "Standard Tax":
                            specs["Standard Tax"] = info
                        elif header == "Insurance":
                            # Check if there's any meaningful info to display
                            insurance_link = row.find('a', class_='popover-link')
                            if insurance_link and insurance_link.text.strip():
                                specs["Insurance"] = insurance_link.text.strip().split('•')[0].strip()
                            else:
                                specs["Insurance"] = "Insurance not found"

            # Extract model and year from the title
            title_header = soup.find('h1', class_='car-detail-header__title')
            if title_header:
                title_text = title_header.get_text(strip=True)
                title_parts = title_text.split()

                # Determine make, year, and model
                for i, part in enumerate(title_parts):
                    if part in self.known_makes:
                        specs['Make'] = part
                        specs['Model'] = ' '.join(
                            title_parts[i + 1:])  # Everything after make is model
                        # Try to find the year in parts before the make
                        for j in range(i):
                            if title_parts[j].isdigit() and len(title_parts[j]) == 4:
                                specs['Year'] = title_parts[j]
                                break
                        break

        except Exception as e:
            print(f"Error extracting specs with BeautifulSoup: {e}")

        return specs

    def save_to_csv(self):
        fieldnames = ['Make', 'Model', 'Year', 'Price', 'Mileage',
                      'Engine', 'Fuel', 'Transmission', 'Body Style', 'Location', 'Standard Tax', 'Insurance', 'Link']
        try:
            with open(f"{self.file_name}.csv", mode='w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                for car in self.car_catalogue:
                    writer.writerow(car)
            print(
                f"Successfully saved {len(self.car_catalogue)} cars to {self.file_name}.csv")
        except IOError as e:
            print(f"Failed to write to CSV: {e}")


def main():
    search_url = "https://www.usedcarsni.com/search_results.php?search_type=1&make=24&fuel_type=2&age_from=2016&price_from=0&user_type=2%7C4&model=1170&trans_type=0&age_to=0&price_to=0&mileage_to=0&keywords=&distance_enabled=1&distance_postcode=&body_style=12&doors%5B%5D=5"
    hyundai10 = "https://www.usedcarsni.com/search_results.php?search_type=1&make=9&fuel_type=0&age_from=0&price_from=0&user_type=0&model=17036939&trans_type=0&age_to=0&price_to=0&mileage_to=0&keywords=&distance_enabled=1&distance_postcode=&body_style=0"
    scraper = CarScraper(hyundai10, 'hyundai10')
    scraper.start()
    scraper.save_to_csv()


if __name__ == '__main__':
    main()
