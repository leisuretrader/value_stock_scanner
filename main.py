import yfinance as yf
import pandas as pd
from datetime import datetime
import requests
from bs4 import BeautifulSoup

def get_company_financials(ticker):
    company = yf.Ticker(ticker)
    bs = company.balancesheet
    is_ = company.financials
    latest_bs = bs[bs.columns[0]]
    latest_is = is_[is_.columns[0]]
    return latest_bs, latest_is, company

def calculate_altman_z_score(latest_bs, latest_is, company):
    x1 = (latest_bs['Current Assets'] - latest_bs['Current Liabilities']) / latest_bs['Total Assets']
    x2 = latest_bs['Retained Earnings'] / latest_bs['Total Assets']
    ebit = latest_is['Gross Profit'] - latest_is['Operating Expense']
    x3 = ebit / latest_bs['Total Assets']
    history = company.history(period="1d")
    close_price = history['Close'][0]
    shares_outstanding = company.info['sharesOutstanding']
    market_value_equity = close_price * shares_outstanding
    x4 = market_value_equity / latest_bs['Total Liabilities Net Minority Interest']
    x5 = latest_is['Total Revenue'] / latest_bs['Total Assets']
    z_score = 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5
    return z_score

def calculate_interest_coverage_ratio(latest_is):
    ebit = latest_is['Gross Profit'] - latest_is['Operating Expense']
    interest_expense = latest_is['Interest Expense']
    if interest_expense == 0:
        return None
    interest_coverage_ratio = ebit / interest_expense
    return interest_coverage_ratio

def calculate_roe(latest_bs, latest_is):
    net_income = latest_is['Net Income']
    shareholders_equity = latest_bs['Total Assets'] - latest_bs['Total Liabilities Net Minority Interest']
    if shareholders_equity == 0:
        return None
    roe = net_income / shareholders_equity * 100
    return roe

def get_ebitda(ticker, company, year=0):
    is_ = company.financials
    if year >= len(is_.columns):
        return None
    selected_year_is = is_[is_.columns[year]]
    net_income = selected_year_is['Net Income']
    interest = selected_year_is.get('Interest Expense')
    taxes = selected_year_is.get('Tax Provision')
    depreciation_amortization = selected_year_is.get('Reconciled Depreciation')
    if None in [net_income, interest, taxes, depreciation_amortization]:
        return None
    ebitda = net_income + interest + taxes + depreciation_amortization
    return ebitda

def check_ebitda_growth(ticker, company):
    ebitda_last_year = get_ebitda(ticker, company, year=0)
    ebitda_year_before_last = get_ebitda(ticker, company, year=1)
    if ebitda_last_year is None or ebitda_year_before_last is None:
        return None
    return ebitda_last_year > ebitda_year_before_last

def get_sp500_tickers():
    resp = requests.get('http://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    soup = BeautifulSoup(resp.text, 'lxml')
    table = soup.find('table', {'class': 'wikitable sortable'})
    tickers = []
    for row in table.findAll('tr')[1:]:
        ticker = row.findAll('td')[0].text.strip()
        tickers.append(ticker)
    return tickers

def stock_scanner(tickers):
    data = []
    for ticker in tickers:
        altman_z_score = calculate_altman_z_score(ticker)
        roe = calculate_roe(ticker)
        operating_cash_flow_positive = get_ten_years_operating_cash_flow(ticker)
        interest_coverage_ratio = calculate_interest_coverage_ratio(ticker)
        ebitda_growth = check_ebitda_growth(ticker)

        data.append([ticker, altman_z_score, roe, operating_cash_flow_positive, interest_coverage_ratio, ebitda_growth])

    df = pd.DataFrame(data, columns=['Ticker', 'Altman Z-score', 'ROE', 'Positive Operating Cash Flow', 'Interest Coverage Ratio', 'EBITDA Growth'])
    return df

def stock_scanner(tickers):

    data = {
        'Ticker': [],
        'Altman Z-Score': [],
        'Interest Coverage Ratio': [],
        'ROE': [],
        'EBITDA Growth': []
    }

    for ticker in tickers:
        try:
            latest_bs, latest_is, company = get_company_financials(ticker)
            altman_z_score = calculate_altman_z_score(latest_bs, latest_is, company)
            interest_coverage_ratio = calculate_interest_coverage_ratio(latest_is)
            roe = calculate_roe(latest_bs, latest_is)
            ebitda_growth = check_ebitda_growth(ticker, company)
            
            if altman_z_score > 4 and interest_coverage_ratio > 0 and roe > 20 and ebitda_growth:
                data['Ticker'].append(ticker)
                data['Altman Z-Score'].append(altman_z_score)
                data['Interest Coverage Ratio'].append(interest_coverage_ratio)
                data['ROE'].append(roe)
                data['EBITDA Growth'].append(ebitda_growth)
        except Exception as e:
            print(f"Could not get data for {ticker}, error: {str(e)}")

    return pd.DataFrame(data)

# spy_df = stock_scanner(get_sp500_tickers())
df = stock_scanner(['GOOGL','V','ENPH'])
print(df)
