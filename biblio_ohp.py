import requests
import argparse

# Mapping des instruments avec leurs télescopes
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
        params={"q": query, "rows": 2000, "fl": "title,bibcode,url,author,abstract"}
    )

    if response.status_code != 200:
        print(f"Error querying ADS: {response.status_code}")
        return []

    articles = response.json().get("response", {}).get("docs", [])
    print(f"Found {len(articles)} articles containing at least one keyword.")
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

    for keyword in keywords:
        query = f'bibcode:"{bibcode}" AND (title:"{keyword}" OR abstract:"{keyword}" OR full:"{keyword}")'
        response = requests.get(
            base_url,
            headers=headers,
            params={"q": query, "rows": 1, "fl": "bibcode"}
        )

        if response.status_code == 200 and response.json().get("response", {}).get("numFound", 0) > 0:
            found_keywords.append(keyword)

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
    total_articles = len(articles)
    html_filename = f"pubs-{year}.html"
    with open(html_filename, "w", encoding="utf-8") as file:
        file.write(f"<html>\n<head><title>Publications {year}</title></head>\n<body>\n")
        file.write(f"<h1>Publications {year}</h1>\n")
        file.write(f"<p><strong>Total articles: {total_articles}</strong></p>\n")

        for article in articles:
            title = " ".join(article.get("title", ["No title"]))
            bibcode = article.get("bibcode", "")
            authors = article.get("author", [])
            instruments = article.get("instruments", [])

            # Format authors
            if len(authors) > 3:
                author_list = f"{', '.join(authors[:3])}, et al."
            else:
                author_list = ", ".join(authors)

            # Format instruments
            instruments_str = " ".join([f"{INSTRUMENT_TELESCOPE_MAP.get(instr, 'Unknown')} / {instr}" for instr in instruments])

            # Write to file
            file.write(f"<p><strong>{instruments_str}</strong><br>\n")
            file.write(f"{author_list}<br>\n")
            file.write(f"<strong>{title}</strong><br>\n")
            file.write(f'<a href="https://ui.adsabs.harvard.edu/abs/{bibcode}/abstract" target="_blank">{bibcode}</a><br>\n</p>\n')

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
    main(args.year, KEYWORDS, API_TOKEN, BIBSTEMS)