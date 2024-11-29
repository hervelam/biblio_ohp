import os
import requests
import argparse
import ast
import time

# Mapping instruments with their telescopes
INSTRUMENT_TELESCOPE_MAP = {
    "ELODIE": "T193",
    "GHASP": "T193",
    "MISTRAL": "T193",
    "SOPHIE": "T193",
    "CARELEC": "T193",
    "AURELIE": "T152",
    "CORAVEL": "T100 Suisse",
    "OHP": "Autre telescope",
}


def fetch_all_articles(year, keywords, api_token, bibstems=None):
    """
    Fetch all articles containing any of the keywords.
    Args:
        year (int): Publication year to search for.
        keywords (list): List of keywords to search for.
        api_token (str): Your ADS API token.
        bibstems (list): Optional list of journal bibstems.

    Returns:
        list: List of articles.
    """
    base_url = "https://api.adsabs.harvard.edu/v1/search/query"
    headers = {"Authorization": f"Bearer {api_token}"}

    # Build query for all keywords
    query_keywords = " OR ".join([f'title:"{kw}" OR abstract:"{kw}" OR full:"{kw}"' for kw in keywords])
    query = f"year:{year} AND ({query_keywords})"
    if bibstems:
        bibstem_query = " OR ".join([f'bibstem:"{bib}"' for bib in bibstems])
        query += f" AND ({bibstem_query})"
    else:
        query += " AND collection:astronomy"

    print(f"Querying ADS with combined keywords: {query}")

    response = requests.get(
        base_url,
        headers=headers,
        params={"q": query, "rows": 2000, "fl": "title,bibcode,url,author,abstract,links_data"}
    )

    if response.status_code != 200:
        print(f"Error querying ADS: {response.status_code}")
        return []

    articles = response.json().get("response", {}).get("docs", [])
    print(f"Found {len(articles)} articles containing at least one instrument.")
    return articles


def verify_keywords_in_article(bibcode, keywords, api_token):
    """
    Verify which keywords are present in an article by its bibcode.
    Args:
        bibcode (str): Bibcode of the article.
        keywords (list): List of keywords to check.
        api_token (str): Your ADS API token.

    Returns:
        list: List of keywords found in the article.
    """
    base_url = "https://api.adsabs.harvard.edu/v1/search/query"
    headers = {"Authorization": f"Bearer {api_token}"}
    found_keywords = []

    print(f"Verifying instruments for article {bibcode}...")

    for keyword in keywords:
        #print(f"Checking keyword: {keyword}")
        query = f'bibcode:"{bibcode}" AND (title:"{keyword}" OR abstract:"{keyword}" OR full:"{keyword}")'
        response = requests.get(
            base_url,
            headers=headers,
            params={"q": query, "rows": 1, "fl": "bibcode"}
        )
        time.sleep(1)

        if response.status_code == 200 and response.json().get("response", {}).get("numFound", 0) > 0:
            found_keywords.append(keyword)
        #if response.status_code == 200:
        #    if response.json().get("response", {}).get("numFound", 0) > 0:
        #        print(f"Keyword '{keyword}' found for {bibcode}.")
        #        found_keywords.append(keyword)
        #    else:
        #        print(f"Keyword '{keyword}' not found for {bibcode}.")
        #else:
        #    print(f"Failed to check keyword '{keyword}' for {bibcode} (HTTP {response.status_code}).")

    print(f"Instruments found for {bibcode}: {found_keywords}")
    return found_keywords


def save_articles_to_html(articles, year):
    """
    Save the list of articles to an HTML file.
    Args:
        articles (list): List of articles with their associated instruments.
        year (int): Year of publication.

    Returns:
        None
    """
    # Create the directory for the articles
    directory_name = f"articles_{year}"
    os.makedirs(directory_name, exist_ok=True)

    # Headers to mimic a browser request
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }

    # Initialize the HTML file
    total_articles = len(articles)
    html_filename = f"pubs-{year}.html"
    with open(html_filename, "w", encoding="utf-8") as file:
        file.write(f"<html>\n<head><title>Publications {year}</title></head>\n<body>\n")
        file.write(f"<h1>Publications {year}</h1>\n")
        file.write(f"<p><strong>Total articles: {total_articles}</strong></p>\n")

        for idx, article in enumerate(articles, start=1):
            title = " ".join(article.get("title", ["No title"]))
            bibcode = article.get("bibcode", "")
            authors = article.get("author", [])
            instruments = article.get("instruments", [])
            links_data = article.get("links_data", [])
            pdf_url = None

            print(f"Processing article {idx}/{total_articles}: {title} ({bibcode})")

            # Extract the PDF URL from links_data
            for link in links_data:
                try:
                    link_info = ast.literal_eval(link)  # Convert JSON-like string to dict
                    if link_info.get("type") == "pdf" and link_info.get("url"):
                        pdf_url = link_info["url"]
                        break
                except Exception as e:
                    print(f"Error parsing links_data for {bibcode}: {e}")

            # Format authors
            if len(authors) > 3:
                author_list = f"{', '.join(authors[:3])}, et al."
            else:
                author_list = ", ".join(authors)

            # Format instruments
            instruments_str = " ".join([f"{INSTRUMENT_TELESCOPE_MAP.get(instr, 'Unknown')} / {instr}" for instr in instruments])

            # Download the PDF if available
            local_pdf_path = "No PDF available"
            if pdf_url:
                print(f"Attempting to download PDF for {bibcode} from {pdf_url}")
                try:
                    response = requests.get(pdf_url, headers=headers, stream=True, allow_redirects=True)
                    if response.status_code == 200:
                        local_pdf_path = os.path.join(directory_name, f"{bibcode}.pdf")
                        with open(local_pdf_path, "wb") as pdf_file:
                            for chunk in response.iter_content(chunk_size=8192):
                                pdf_file.write(chunk)
                        print(f"PDF successfully downloaded for {bibcode}")
                    else:
                        print(f"Failed to download PDF for {bibcode} (HTTP {response.status_code})")
                        print(f"Final URL after redirection: {response.url}")
                except Exception as e:
                    print(f"Error downloading PDF for {bibcode}: {e}")
            else:
                print(f"No PDF URL found for {bibcode}.")

            time.sleep(1)

            # Write to the HTML file
            file.write(f"<p><strong>{instruments_str}</strong><br>\n")
            file.write(f"{author_list}<br>\n")
            file.write(f"<strong>{title}</strong><br>\n")
            file.write(f'<a href="https://ui.adsabs.harvard.edu/abs/{bibcode}/abstract" target="_blank">{bibcode}</a><br>\n</p>\n')
            if pdf_url and local_pdf_path != "No PDF available":
                file.write(f'<a href="{local_pdf_path}" target="_blank">Download PDF</a><br>\n</p>\n')
            else:
                file.write(f"<em>No PDF available</em><br>\n</p>\n")

        file.write("</body>\n</html>")

    print(f"HTML file '{html_filename}' has been created with a total of {total_articles} articles.")


def main(year, keywords, api_token, bibstems=None):
    """
    Main function to search ADS and save results to an HTML file.
    Args:
        year (int): Publication year to search.
        keywords (list): Keywords to search for.
        api_token (str): Your ADS API token.
        bibstems (list): Optional list of journal bibstems.

    Returns:
        None
    """
    articles = fetch_all_articles(year, keywords, api_token, bibstems)

    # Verify keywords for each article
    for article in articles:
        bibcode = article["bibcode"]
        found_keywords = verify_keywords_in_article(bibcode, keywords, api_token)
        article["instruments"] = []

        if found_keywords:
            if "OHP" in found_keywords and len(found_keywords) == 1:
                article["instruments"].append("OHP")
            else:
                article["instruments"].extend([kw for kw in found_keywords if kw != "OHP"])

    save_articles_to_html(articles, year)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and process ADS articles based on keywords.")
    parser.add_argument("year", type=int, help="Year of publication to search for (e.g., 2024).")
    args = parser.parse_args()

    API_TOKEN = "Replace with your ADS API token"  # Replace with your ADS API token
    KEYWORDS = ["AURELIE", "CORAVEL", "ELODIE", "GHASP", "MISTRAL", "SOPHIE", "OHP"]
    BIBSTEMS = ["A&A", "ApJ", "AJ", "MNRAS"]

    # For small tests
    #KEYWORDS = ["K-Stacker"]
    #BIBSTEMS = ["A&A"]
    #main(2022, KEYWORDS, API_TOKEN, BIBSTEMS)

    main(args.year, KEYWORDS, API_TOKEN, BIBSTEMS)
