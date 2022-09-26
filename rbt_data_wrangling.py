import pandas as pd
import numpy as np
from numpy.core.defchararray import find

import glob
import os

import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# INITIAL DATA ****************************************************************************************************************************************************

# To construct the database for analysis, we'll synthesize several independent datasets:

# DATA ON CONSOLIDATED REGIONAL BUDGETS' EXECUTION (FROM THE RUSSIAN FEDERAL TREASURY)
# For each year between 2011 and 2021, the Treasury has published a dataset containing 85 XLS files, each containing a dataframe on budget revenues and a dataframe 
# on budget spending.

# FEDERAL BUDGET EXECUTION DATA (FROM THE RUSSIAN FEDERAL TREASURY) 
# The federal budget dataset contains 11 XLS files, each with a dataframe for revenues and expenditures.

# TAX DATA (PROVIDED BY THE RUSSIAN MINISTRY OF FINANCE)
# Almost all VAT and mining taxes collected in regions go directly to the federal budget and are absent in the Treasury data on regions. We need data from the
# Ministry of Finance to estimate the total amount of collected taxes.

# POPULATION DATA (FEDERAL STATISTICS SERVICE OF RUSSIA)
# The population data is needed to count budget spending per capita.

# DATA ON REAL INCOME, PER CAPITA INCOME, AND POVERTY LEVEL FOR EACH REGION (FEDERAL STATISTICS SERVICE OF RUSSIA)
# Is needed to estimate the changes in their dwellers wealth.

# THE BANK OF RUSSIA'S ANNUAL USDRUB EXCHANGE RATES
# Will also be used for estimating per capita spending.

# DOWNLOADING ADDITIONAL DATASETS *********************************************************************************************************************************

# The main datasets will be downloaded further within loops

codes_revenue = pd.read_excel('additional_data/budget_codes_eng.xlsx') # English translations of revenue budget codes
codes_spending = pd.read_excel('additional_data/budget_codes_eng.xlsx', sheet_name=1) # English translations of revenue budget codes
regions = pd.read_excel('additional_data/ru_regions_names_and_pop.xlsx', index_col=0) # regions' budget codes, names and population
real_income = pd.read_excel('additional_data/real_income_regions.xlsx', index_col=0) # real income
income_percap = pd.read_excel('additional_data/income_per_cap_regions.xlsx', index_col=0) # income per capita
poverty = pd.read_csv('additional_data/poverty_regions.csv', index_col=0) # poverty level in %
taxes = pd.read_excel('additional_data/taxes_to_budgets.xls') 

# DATASET 1: REGIONAL BUDGETS *************************************************************************************************************************************

# For each year, there's a Treasury database, containing an XLS file for each of the 85 Russian regions, with separate sheets for the revenues and for spending. 
# In this chunk, we'll collect this data into a single dictionary with a year (2011–2021), a region code (1–85), and type of money flow (revenues, spending) as
# keys. A loop will turn to each year's folder, read all the XLS files in it, find the pages we are interested in, and append them to the dictionary (x for revenue,
# y for spending).

path_directory = r"./budget_data/reg/reg_20??" # reading all the regional folders for 2000s from the directory
year_dirs = glob.glob(path_directory)

budget_dict = dict()

for year_dir in year_dirs:
    year = int(year_dir[-4:]) # getting the year number from the folder name
    
    budget_dict[year] = []
    
    files = glob.glob(os.path.join(year_dir, "*.xls")) # reading all XLS files from the folder
    
    # Typically, the regional budget XLS file has four tabs, with the first one for revenues and the second for spending.
    # But older files (up to 2016) also have hidden sheets with metadata as the first sheets, so we'll index them separately
    # to ignore these sheets.
    
    if year >= 2017: 
        for f in files:
            x= pd.read_excel(f)
            x['filename'] = f # filenames are needed to extract unique region numbers
            y= pd.read_excel(f, sheet_name=1)
            y['filename'] = f
            budget_dict[year].append([x, y])
    else:
        for f in files:
            x= pd.read_excel(f, sheet_name=1)
            x['filename'] = f
            y= pd.read_excel(f, sheet_name=2)
            y['filename'] = f
            budget_dict[year].append([x, y])

# In this chunk, we create a loop that will iterate over 1,870 datasets in the dictionary, find the columns we are interested in, and replace the old dataframe
# with the new 4-column dataframe.

years = pd.Series(range(2011,2022))

for year in years:
    
    for index in range(len(budget_dict[year])):
        
        inc = budget_dict[year][index][0]
        spnd = budget_dict[year][index][1]
        
        inc = inc.applymap(lambda s: s.lower() if type(s) == str else s)
        spnd = spnd.applymap(lambda s: s.lower() if type(s) == str else s)
        
        # REVENUES
        
        # fixing some mess in the frames for the 2016 to make all the columns findable:
        inc = inc.replace('-', '', regex=True) 
        inc = inc.replace('\n', '', regex=True)
        inc = inc.replace('ро ванный', 'рованный', regex=True)
        
        # locating the columns by the unique substrings:
        a = inc.columns[(find(inc.to_numpy().astype(str), 'в том числе') >= 0).any(0)][0]
        inc['revenue_type_rus'] = inc[a]
        b = inc.columns[(find(inc.to_numpy().astype(str), 'консолидированный бюджет субъекта') >= 0).any(0)][-1] 
        inc['revenue'] = inc[b]
        c = inc.columns[(find(inc.to_numpy().astype(str), '10000000000000000') >= 0).any(0)][0] 
        inc['revenue_id'] = inc[c]
        
        # replacing the old dataframe with a new 4-column dataframe:
        budget_dict[year][index][0] = inc[['revenue_type_rus', 'revenue_id', 'revenue',
                                           'filename']].dropna().reset_index(drop=True)
        
        # SPENDING
        
        # filling the total spending row in order to not lose it when executing dropna():
        spnd[spnd['Unnamed: 1']=='200'] = spnd[spnd['Unnamed: 1']=='200'].fillna(0)
        
        # locating the columns by the unique substrings...
        x = spnd.columns[(find(spnd.to_numpy().astype(str), 'в том числе') >= 0).any(0)][0] 
        spnd['spending_type_rus'] = spnd[x]
        
        # ...or by their fixed position towards the located column:
        spnd['spending_id_1'] = spnd.iloc[:, spnd.columns.get_loc(x) + 3]
        
        if year < 2015:
            spnd['spending_id_2'] = spnd.iloc[:, spnd.columns.get_loc(x) + 6]
        else:
            spnd['spending_id_2'] = spnd.iloc[:, spnd.columns.get_loc(x) + 5]
        
        z = spnd.columns[(find(spnd.to_numpy().astype(str), 'ванный бюджет субъекта') >= 0).any(0)][-1] 
        spnd['spending'] = spnd[z]
        
        # replacing the dataframe:
        budget_dict[year][index][1] = spnd[['spending_type_rus', 'spending_id_1', 'spending_id_2',
                                            'spending', 'filename']].dropna().reset_index(drop=True)
        
# Now we'll create lists out of our dataframes and then concatenate them within a nested loop:

year_list_rev = [] # a list of future 2011, 2012, etc. dataframes
year_list_spnd = []

for year in years:
    
    df_list_rev = [] # a list of 85 regional dataframes for the year
    df_list_spnd = []
    
    for index in range(len(budget_dict[year])):
        
        x = budget_dict[year][index][0]
        y = budget_dict[year][index][1]
        
        df_list_rev.append(x) # appending each dataframe for the specific year to a list
        df_list_spnd.append(y)
    
    df_year_rev = pd.concat(df_list_rev, ignore_index=True) # concatinating all the data frames for the specific year
    df_year_spnd = pd.concat(df_list_spnd, ignore_index=True)
    
    df_year_rev['year'] = year # appending a column with a year number to each year's dataframe
    df_year_spnd['year'] = year
    
    year_list_rev.append(df_year_rev) # appending each unified data frame to a list
    year_list_spnd.append(df_year_spnd)

revenue = pd.concat(year_list_rev, ignore_index=True) # concatinating all revenue data frames into a single one
spending = pd.concat(year_list_spnd, ignore_index=True) # same for spending

# Tidying the data 

# extracting the 2-digit region number into a new column and getting rid of the filename column:
revenue['region_id'] = [x[27:29] for x in revenue['filename']] 
spending['region_id'] = [x[27:29] for x in spending['filename']]
revenue = revenue.drop('filename', axis=1)
spending = spending.drop('filename', axis=1)
revenue['region_id'] = pd.to_numeric(revenue['region_id']).astype('int') 
spending['region_id'] = pd.to_numeric(spending['region_id']).astype('int')

# cleaning the revenue and spending columns and making them numeric:
revenue['revenue'] = revenue[
    'revenue'].replace('консолидированный бюджет субъекта рф и бюджета территориального государственного внебюджетного фонда',
                       np.nan, regex=True)
revenue['revenue'] = revenue['revenue'].replace(',', '.', regex=True)
revenue['revenue'] = revenue['revenue'].replace('\xa0', '', regex=True)
revenue['revenue'] = pd.to_numeric(revenue['revenue'])

spending['spending'] = spending['spending'].replace(' ', '', regex=True) 
spending['spending'] = spending['spending'].replace(',', '.', regex=True) 
spending['spending'] = spending['spending'].replace('\xa0', '', regex=True) 
spending['spending'] = pd.to_numeric(spending['spending'])

# fixing the id columns types:
spending['spending_id_1'] = spending['spending_id_1'].astype('int')
spending['spending_id_2'] = spending['spending_id_2'].astype('int')

# replacing some noise from the revenue id column:
revenue['revenue_id'] = revenue['revenue_id'].replace(' ', '', regex=True) 
revenue = revenue[revenue['revenue_id'] != "х"]

# We also need the key budget items translated into English. Here I'll use the data collected from the Minfin documents, which contain translations for the main
# revenue and spending items.

codes_revenue['revenue_indicator'] = codes_revenue['revenue_indicator'].str.lower()
codes_spending['spending_indicator'] = codes_spending['spending_indicator'].str.lower()

codes_revenue['code'] = codes_revenue['code'].apply("{:.0f}".format)
codes_revenue['code'] = codes_revenue['code'].astype('str')

revenue = revenue.set_index('revenue_id').join(codes_revenue.rename(columns={'code':'revenue_id'}).set_index(
    'revenue_id'), how='left').reset_index().rename(columns={'revenue_indicator':'revenue_type_eng'})

spending = spending.set_index('spending_id_1').join(codes_spending.rename(columns={'code':'spending_id_1'}).set_index(
    'spending_id_1'), how='left').reset_index().rename(columns={'spending_indicator':'spending_type_eng'})

# DATASETS 2-5: POPULATION, EARNINGS, POVERTY, USDRUB *************************************************************************************************************

# Yearly USDRUB eachange rate, from the Central Bank of Russia:
rubusd = [[2011,29.3925],[2012,31.088],[2013,31.8542],[2014,38.4375],[2015,60.9579],[2016,67.0349],
          [2017,58.3529],[2018,62.7091],[2019,64.7362],[2020,72.1464],[2021,73.6541]]
rubusd = pd.DataFrame(rubusd, columns=['year', 'rub_usd']).set_index('year')

# fixing the data types
regions = regions.fillna(0)
regions[2011] = regions[2011].astype('int')
regions[2012] = regions[2012].astype('int')
regions[2013] = regions[2013].astype('int')

income_percap['2011'] = income_percap['2011'].fillna(0)
income_percap['2012'] = income_percap['2012'].fillna(0)
income_percap['2011'] = income_percap['2011'].astype('int')
income_percap['2012'] = income_percap['2012'].astype('int')

poverty = poverty.rename(columns={'2011': 2011,'2012': 2012,'2013': 2013,'2014': 2014, '2015': 2015,'2016': 2016,'2017': 2017,
                                  '2018': 2018,'2019': 2019,'2020': 2020,'2021': 2021})

# transforming the population dataframe
reg_names = pd.melt(regions.reset_index(), id_vars=['budget_code', 'region_eng', 'region_rus'],
                    value_vars=[2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021])
reg_names = reg_names.rename(columns={'variable':'year', 'value':'population'}).set_index(['budget_code', 'year'])
reg_names = reg_names.applymap(lambda s: s.lower() if type(s)==str else s)

# transforming the poverty dataframe
reg_poverty = pd.melt(poverty.reset_index(), id_vars=['budget_code', 'region_eng', 'region_rus'],
                      value_vars=[2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021])
reg_poverty = reg_poverty.rename(columns={'variable':'year', 'value':'poverty'}).set_index(['budget_code', 'year'])
reg_poverty = reg_poverty.applymap(lambda s: s.lower() if type(s)==str else s)

# transforming the real income dataframe
reg_realinc = pd.melt(real_income.reset_index(), id_vars=['budget_code', 'region_eng', 'region_rus'],
                    value_vars=['2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021'])
reg_realinc = reg_realinc.rename(columns={'variable':'year', 'value':'real_income'})
reg_realinc['year'] = pd.to_numeric(reg_realinc['year']).astype('int')
reg_realinc = reg_realinc.set_index(['budget_code', 'year'])
reg_realinc = reg_realinc.applymap(lambda s: s.lower() if type(s)==str else s)

# transforming the income per capita dataframe
reg_incpercap = pd.melt(income_percap.reset_index(), id_vars=['budget_code','region_eng','region_rus'],
                        value_vars=['2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021'])
reg_incpercap = reg_incpercap.rename(columns={'variable':'year', 'value':'income_per_cap'})
reg_incpercap['year'] = pd.to_numeric(reg_incpercap['year']).astype('int')
reg_incpercap = reg_incpercap.set_index(['budget_code', 'year'])
reg_incpercap = reg_incpercap.applymap(lambda s: s.lower() if type(s)==str else s)

# joining new data to the regional dataframes 
revenue = revenue.rename(columns={'region_id':'budget_code'}).set_index(['budget_code', 'year'])
spending = spending.rename(columns={'region_id':'budget_code'}).set_index(['budget_code', 'year'])
revenue = revenue.join([reg_names, reg_realinc[['real_income']], reg_incpercap[['income_per_cap']], reg_poverty[['poverty']]], how='left')
spending = spending.join([reg_names, reg_realinc[['real_income']], reg_incpercap[['income_per_cap']], reg_poverty[['poverty']]], how='left')
revenue = revenue.reset_index().drop('budget_code', axis=1)
spending = spending.reset_index().drop('budget_code', axis=1)
revenue = revenue.set_index('year').join(rubusd).reset_index()
spending = spending.set_index('year').join(rubusd).reset_index()

revenue['population'] = revenue['population'].astype('int')
spending['population'] = spending['population'].astype('int')

# DATASET 6: TAXES ************************************************************************************************************************************************

taxes = taxes.rename(columns={'Unnamed: 0':'region', 'Unnamed: 1':'tax'})

#  First of all, let's extract the type of budget substring to a separate column:

# we'll have to filter by substrings a lot, so it's better to convert all strings to lower case
taxes = taxes.applymap(lambda s: s.lower() if type(s) == str else s) 

# assigning variables to filter rows by substrings: 
total = taxes['tax'].str.contains("- всего", case=False) # "всего" stands for "total sum transferred"
federal = taxes['tax'].str.contains("в федеральный бюджет", case=False) # = "to federal budget"
regional = taxes['tax'].str.contains("бюджеты субъектов", case=False) # = "to regional budgets"
federal_funds = taxes['tax'].str.contains("фонда", case=False) # = "to federal non-budget funds"
regional_funds = taxes['tax'].str.contains("территориальных фондов", case=False) # = "to regional non-budget funds"

# creating a new "budget" column with these variables:
taxes.loc[total, 'budget'] = 'total'
taxes.loc[federal, 'budget'] = 'federal'
taxes.loc[regional, 'budget'] = 'regional'
taxes.loc[federal_funds, 'budget'] = 'federal_funds'
taxes.loc[regional_funds, 'budget'] = 'regional_funds'

# The assignment of codes to taxes

# assigning variables to filter rows by taxes names:
excise_import = taxes['tax'].str.contains("акцизы по подакцизным товарам \(\продукции\)\, ввозимым на территорию российской федерации", case=False)
excise_rus = taxes['tax'].str.contains("производимым на территории российской федерации", case=False)
water_tax = taxes['tax'].str.contains("водный налог", case=False)
state_duty = taxes['tax'].str.contains("государственная пошлина", case=False)
presumptive_tax = taxes['tax'].str.contains("единый налог на вмененный доход", case=False)
agricultural_tax = taxes['tax'].str.contains("единый сельскохозяйственный налог", case=False)
vat_sales = taxes['tax'].str.contains("налог на добавленную стоимость на товары \(\работы, услуги\)\, реализуемые", case=False)
vat_import = taxes['tax'].str.contains("налог на добавленную стоимость на товары, ввозимые", case=False)
gas_extraction_tax = taxes['tax'].str.contains("налог на добычу газа", case=False)
gas_condensate_extraction_tax = taxes['tax'].str.contains("налог на добычу газового конденсата", case=False)
oil_extraction_tax = taxes['tax'].str.contains("налог на добычу нефти", case=False)
mining_tax = taxes['tax'].str.contains("налог на добычу полезных ископаемых", case=False)
add_income_hydrocarbon_tax = taxes['tax'].str.contains("налог на дополнительный доход от добычи углеводородного сырья", case=False)
personal_income_tax = taxes['tax'].str.contains("налог на доходы физических лиц", case=False)
gambling_tax = taxes['tax'].str.contains("налог на игорный бизнес", case=False)
property_tax = taxes['tax'].str.contains("налог на имущество", case=False)
corporate_income_tax = (taxes['tax'].str.contains("налог на прибыль организаций", case=False) & (~taxes['tax'].str.contains("при выполнении соглашений", case=False)))
corporate_income_tax_sharing = taxes['tax'].str.contains("налог на прибыль организаций при выполнении соглашений о разделе продукции", case=False)
professional_income = taxes['tax'].str.contains("налог на профессиональный доход", case=False)
simplified_patent = taxes['tax'].str.contains("налог, взимаемый в виде стоимости патента", case=False)
patent_tax = taxes['tax'].str.contains("налог, взимаемый в связи с применением патентной", case=False)
simplified_all = taxes['tax'].str.contains("налог, взимаемый в связи с применением упрощенной системы", case=False)
subsoil_use_payments = taxes['tax'].str.contains("платежи за пользование недрами", case=False)
regular_mining_payments = taxes['tax'].str.contains("роялти", case=False)
biological_resources_use_fee = taxes['tax'].str.contains("животного мира", case=False)
transport_tax = taxes['tax'].str.contains("транспортный налог", case=False)
total_revenue = taxes['tax'].str.contains("поступило", case=False)

# creating new columns with budget codes and ENG/RUS names corresponding to these variables:
taxes.loc[excise_import, ['tax_code', 'tax_eng', 'tax_rus']] = ['10402000010000110', 'excises on imported goods', 'акцизы по ввозимым товарам']
taxes.loc[excise_rus, ['tax_code', 'tax_eng', 'tax_rus']] = ['10302000010000110', 'excises', 'акцизы по производимым товарам']
taxes.loc[water_tax, ['tax_code', 'tax_eng', 'tax_rus']] = ['10703000010000110', 'water tax', 'водный налог']
taxes.loc[state_duty, ['tax_code', 'tax_eng', 'tax_rus']] = ['10800000000000000', 'state duty', 'государственная пошлина']
taxes.loc[presumptive_tax, ['tax_code', 'tax_eng', 'tax_rus']] = ['10502000020000110', 'presumptive tax', 'единый налог на вмененный доход']
taxes.loc[agricultural_tax, ['tax_code', 'tax_eng', 'tax_rus']] = ['10503000010000110', 'unified agricultural tax', 'единый сельскохозяйственный налог']
taxes.loc[vat_sales, ['tax_code', 'tax_eng', 'tax_rus']] = ['10301000010000110', 'vat on sales', 'ндс на реализуемые товары']
taxes.loc[vat_import, ['tax_code', 'tax_eng', 'tax_rus']] = ['10401000010000110', 'vat on import', 'ндс на ввозимые товары']
taxes.loc[gas_extraction_tax, ['tax_code', 'tax_eng', 'tax_rus']] = ['10701012010000110', 'gas extraction tax', 'налог на добычу газа']
taxes.loc[gas_condensate_extraction_tax, ['tax_code', 'tax_eng', 'tax_rus']] = ['10701013010000110', 'gas condensate extraction tax', 'налог на добычу газового конденсата']
taxes.loc[oil_extraction_tax, ['tax_code', 'tax_eng', 'tax_rus']] = ['10701011010000110', 'oil extraction tax', 'налог на добычу нефти']
taxes.loc[mining_tax, ['tax_code', 'tax_eng', 'tax_rus']] = ['10701000010000110', 'minerals extraction tax', 'налог на добычу полезных ископаемых']
taxes.loc[add_income_hydrocarbon_tax, ['tax_code', 'tax_eng', 'tax_rus']] = ['10705000010000110', 'additional income from hydrocarbon extraction tax', 'налог на дополнительный доход от добычи углеводородного сырья']
taxes.loc[personal_income_tax, ['tax_code', 'tax_eng', 'tax_rus']] = ['10102000010000110', 'personal income tax', 'ндфл']
taxes.loc[gambling_tax, ['tax_code', 'tax_eng', 'tax_rus']] = ['10605000020000110', 'gambling tax', 'налог на игорный бизнес']
taxes.loc[property_tax, ['tax_code', 'tax_eng', 'tax_rus']] = ['10600000000000000', 'property taxes', 'налог на имущество']
taxes.loc[corporate_income_tax, ['tax_code', 'tax_eng', 'tax_rus']] = ['10101000000000110', 'corporate income tax full', 'налог на прибыль организаций']
taxes.loc[corporate_income_tax_sharing, ['tax_code', 'tax_eng', 'tax_rus']] = ['10101020010000110', 
                                                                               'corporate income tax on the implementation of oil and gas fields development agreements',
                                                                               'налог на прибыль организаций при выполнении соглашений о разработке месторождений нефти и газа']
taxes.loc[professional_income, ['tax_code', 'tax_eng', 'tax_rus']] = ['10506000010000110', 'professional income tax', 'налог на профессиональный доход']
taxes.loc[simplified_patent, ['tax_code', 'tax_eng', 'tax_rus']] = ['10911000020000110', 'patent cost via the simplified taxation system', 
                                                                    'налог в виде стоимости патента в связи с применением упрощенной системы налогообложения']
taxes.loc[patent_tax, ['tax_code', 'tax_eng', 'tax_rus']] = ['10504000020000110', 'patent taxation system', 
                                                             'налог взимаемый в связи с применением патентной системы налогообложения']
taxes.loc[simplified_all, ['tax_code', 'tax_eng', 'tax_rus']] = ['10501000000000110', 'simplified tax system',
                                                                 'налог на профессиональный доход в связи с применением упрощенной системы налогообложения']
taxes.loc[subsoil_use_payments, ['tax_code', 'tax_eng', 'tax_rus']] = ['10903060010000110', 'subsoil use payments', 'платежи за пользование недрами']
taxes.loc[regular_mining_payments, ['tax_code', 'tax_eng', 'tax_rus']] = ['10702000010000110', 'regular mining payments', 
                                                                          'регулярные платежи за добычу полезных ископаемых (роялти)']
taxes.loc[biological_resources_use_fee, ['tax_code', 'tax_eng', 'tax_rus']] = ['10704000010000110', 'biological resources use fee',
                                                                               'сборы за пользование объктами животного мира']
taxes.loc[transport_tax, ['tax_code', 'tax_eng', 'tax_rus']] = ['10604000020000110', 'transport tax', 'транспортный налог']
taxes.loc[total_revenue, ['tax_code', 'tax_eng', 'tax_rus']] = ['00000000000000000', 'total tax revenue', 'всего поступило налогов'] 

# Now that we've added all the necessary columns, let's transform the dataframe:

taxes = taxes.drop('tax', axis=1)

# first, we create a long data from wide:
taxes_1 = pd.melt(taxes, id_vars=['region', 'tax_rus', 'tax_eng', 'tax_code', 'budget'],
                  value_vars=['2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021'])
taxes_1 = taxes_1.rename(columns={'variable':'year', 'value':'sum'})
taxes_1['sum'] = taxes_1['sum']*1000 # Minfin gives sums in RUB'000, the Treasury in RUB 

# next, we create wide data, breaking the 'budget' column into separate columns for each budget type:
taxes_fin = taxes_1.pivot_table(index=['year', 'region', 'tax_code', 'tax_rus', 'tax_eng'], columns='budget', values='sum').fillna(0).reset_index()

# Extracting regions' names 

taxes_fin.loc[taxes_fin['region'].str.contains("башкортостан", case=False), 'region_eng'] = 'Bashkortostan'
taxes_fin.loc[taxes_fin['region'].str.contains("бурятия", case=False), 'region_eng'] = 'Buryatia'
taxes_fin.loc[taxes_fin['region'].str.contains("дагестан", case=False), 'region_eng'] = 'Dagestan'
taxes_fin.loc[taxes_fin['region'].str.contains("кабардино", case=False), 'region_eng'] = 'Kabardino-Balkaria'
taxes_fin.loc[taxes_fin['region'].str.contains("калмыкия", case=False), 'region_eng'] = 'Kalmykia'
taxes_fin.loc[taxes_fin['region'].str.contains("карелия", case=False), 'region_eng'] = 'Karelia'
taxes_fin.loc[taxes_fin['region'].str.contains("коми", case=False), 'region_eng'] = 'Komi'
taxes_fin.loc[taxes_fin['region'].str.contains("марий", case=False), 'region_eng'] = 'Mariy El'
taxes_fin.loc[taxes_fin['region'].str.contains("мордовия", case=False), 'region_eng'] = 'Mordovia'
taxes_fin.loc[taxes_fin['region'].str.contains("осетия", case=False), 'region_eng'] = 'North Osetia - Alania'
taxes_fin.loc[taxes_fin['region'].str.contains("татарстан", case=False), 'region_eng'] = 'Tatarstan'
taxes_fin.loc[taxes_fin['region'].str.contains("тыва", case=False), 'region_eng'] = 'Tyva'
taxes_fin.loc[taxes_fin['region'].str.contains("удмуртская", case=False), 'region_eng'] = 'Udmurtia'
taxes_fin.loc[taxes_fin['region'].str.contains("ингушетия", case=False), 'region_eng'] = 'Ingushetia'
taxes_fin.loc[taxes_fin['region'].str.contains("чувашская", case=False), 'region_eng'] = 'Chuvashia'
taxes_fin.loc[taxes_fin['region'].str.contains("якутия", case=False), 'region_eng'] = 'Sakha (Yakutia)'
taxes_fin.loc[taxes_fin['region'].str.contains("алтайский", case=False), 'region_eng'] = 'Altai Krai'
taxes_fin.loc[taxes_fin['region'].str.contains("краснодарский", case=False), 'region_eng'] = 'Krasnodarsky Krai'
taxes_fin.loc[taxes_fin['region'].str.contains("красноярский", case=False), 'region_eng'] = 'Krasnoyarsky Krai'
taxes_fin.loc[taxes_fin['region'].str.contains("приморский", case=False), 'region_eng'] = 'Primorsky Krai'
taxes_fin.loc[taxes_fin['region'].str.contains("ставропольский", case=False), 'region_eng'] = 'Stavropolsky Krai'
taxes_fin.loc[taxes_fin['region'].str.contains("хабаровский", case=False), 'region_eng'] = 'Khabarovsky Krai'
taxes_fin.loc[taxes_fin['region'].str.contains("амурская", case=False), 'region_eng'] = 'Amur Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("архангельская", case=False), 'region_eng'] = 'Arkhangelsk Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("астраханская", case=False), 'region_eng'] = 'Astrakhan Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("белгородская", case=False), 'region_eng'] = 'Belgorod Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("брянская", case=False), 'region_eng'] = 'Bryansk Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("владимирская", case=False), 'region_eng'] = 'Vladimir Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("волгоградская", case=False), 'region_eng'] = 'Volgograd Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("вологодская", case=False), 'region_eng'] = 'Vologda Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("воронежская", case=False), 'region_eng'] = 'Voronezh Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("нижегородская", case=False), 'region_eng'] = 'Nizhny Novgorod Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("ивановская", case=False), 'region_eng'] = 'Ivanovo Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("иркутская", case=False), 'region_eng'] = 'Irkutsk Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("калининградская", case=False), 'region_eng'] = 'Kaliningrad Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("тверская", case=False), 'region_eng'] = 'Tver Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("калужская", case=False), 'region_eng'] = 'Kaluga Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("камчатский", case=False), 'region_eng'] = 'Kamchatsky Krai'
taxes_fin.loc[taxes_fin['region'].str.contains("кемеровская", case=False), 'region_eng'] = 'Kemerovo Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("кировская", case=False), 'region_eng'] = 'Kirov Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("костромская", case=False), 'region_eng'] = 'Kostroma Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("самарская", case=False), 'region_eng'] = 'Samara Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("курганская", case=False), 'region_eng'] = 'Kurgan Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("курская", case=False), 'region_eng'] = 'Kursk Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("ленинградская", case=False), 'region_eng'] = 'Leningrad Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("липецкая", case=False), 'region_eng'] = 'Lipetsk Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("магаданская", case=False), 'region_eng'] = 'Magadan Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("московская", case=False), 'region_eng'] = 'Moscow Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("мурманская", case=False), 'region_eng'] = 'Murmansk Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("новгородская", case=False), 'region_eng'] = 'Novgorod Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("новосибирская", case=False), 'region_eng'] = 'Novosibirsk Oblast'
taxes_fin.loc[(taxes_fin['region'].str.contains("омская", case=False) & (~taxes_fin['region'].str.contains("костро", case=False))), 'region_eng'] = 'Omsk Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("оренбургская", case=False), 'region_eng'] = 'Orenburg Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("орловская", case=False), 'region_eng'] = 'Orel Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("пензенская", case=False), 'region_eng'] = 'Penza Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("пермский", case=False), 'region_eng'] = 'Permsky Krai'
taxes_fin.loc[taxes_fin['region'].str.contains("псковская", case=False), 'region_eng'] = 'Pskov Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("ростовская", case=False), 'region_eng'] = 'Rostov Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("рязанская", case=False), 'region_eng'] = 'Ryazan Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("саратовская", case=False), 'region_eng'] = 'Saratov Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("сахалинская", case=False), 'region_eng'] = 'Sakhalin Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("свердловская", case=False), 'region_eng'] = 'Sverdlov Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("смоленская", case=False), 'region_eng'] = 'Smolensk Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("тамбовская", case=False), 'region_eng'] = 'Tambov Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("томская", case=False), 'region_eng'] = 'Tomsk Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("тульская", case=False), 'region_eng'] = 'Tula Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("тюменская", case=False), 'region_eng'] = 'Tyumen Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("ульяновская", case=False), 'region_eng'] = 'Ulyanovsk Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("челябинская", case=False), 'region_eng'] = 'Chelyabinsk Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("ярославская", case=False), 'region_eng'] = 'Yaroslavl Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("петербург", case=False), 'region_eng'] = 'Saint Petersburg'
taxes_fin.loc[taxes_fin['region'].str.contains("москва", case=False), 'region_eng'] = 'Moscow'
taxes_fin.loc[taxes_fin['region'].str.contains("севастополь", case=False), 'region_eng'] = 'Sevastopol'
taxes_fin.loc[taxes_fin['region'].str.contains("крым", case=False), 'region_eng'] = 'Crimea'
taxes_fin.loc[taxes_fin['region'].str.contains("адыгея", case=False), 'region_eng'] = 'Adygea'
taxes_fin.loc[(taxes_fin['region'].str.contains("алтай", case=False) & (~taxes_fin['region'].str.contains("край", case=False))), 'region_eng'] = 'Altai'
taxes_fin.loc[taxes_fin['region'].str.contains("еврейская", case=False), 'region_eng'] = 'Jewish Autonomous Oblast'
taxes_fin.loc[taxes_fin['region'].str.contains("карачаево", case=False), 'region_eng'] = 'Karachaevo-Cherkessia'
taxes_fin.loc[taxes_fin['region'].str.contains("хакасия", case=False), 'region_eng'] = 'Hakasia'
taxes_fin.loc[(taxes_fin['region'].str.contains("ненецкий", case=False) & (~taxes_fin['region'].str.contains("ямало", case=False))), 'region_eng'] = 'Nenets Autonomous Okrug'
taxes_fin.loc[taxes_fin['region'].str.contains("ханты", case=False), 'region_eng'] = 'Khanty-Mansiysk Autonomous Okrug – Ugra'
taxes_fin.loc[taxes_fin['region'].str.contains("чукотский", case=False), 'region_eng'] = 'Chukotka Autonomous Okrug'
taxes_fin.loc[taxes_fin['region'].str.contains("ямало", case=False), 'region_eng'] = 'Yamalo-Nenets Autonomous Okrug'
taxes_fin.loc[taxes_fin['region'].str.contains("забайкальский", case=False), 'region_eng'] = 'Zabaykalsky Krai'
taxes_fin.loc[taxes_fin['region'].str.contains("чеченская", case=False), 'region_eng'] = 'Chechnya'
taxes_fin.loc[taxes_fin['region'].str.contains("российская федерация", case=False), 'region_eng'] = 'Russia'

taxes_fin['region_eng'] = taxes_fin['region_eng'].str.lower()
taxes_fin = taxes_fin.drop('region', axis=1)

# Joining taxes to budgets 

# The first column calculates the total sum of taxes transferred to the federal level, namely, to the federal budget and to
# the budgets of federal state non-budget funds

taxes_fin['tax_to_fed'] = taxes_fin['federal']+taxes_fin['federal_funds']

# The second column estimates the sum of taxes transferred to the region solely (without regional non-budget fund). We need
# this column only to compare the budget and the tax data for disparities between the transferred and registered money.
taxes_fin = taxes_fin.rename(columns={'regional':'tax_to_region'})
taxes_fin = taxes_fin.drop(['federal', 'federal_funds', 'regional_funds', 'total'], axis=1)

# joining the dataframes
taxes_fin['year'] = taxes_fin['year'].astype('int')
taxes_fin = taxes_fin.rename(columns = {'tax_code':'revenue_id'})
taxes_fin = taxes_fin.set_index(['year', 'region_eng', 'revenue_id'])

revenue_fin = revenue.set_index(['year', 'region_eng', 'revenue_id']).join(taxes_fin, how='outer').reset_index()

# filling the missing revenue names in the main dataframe with those from the taxes data
revenue_fin['revenue_type_rus'] = revenue_fin['revenue_type_rus'].fillna(revenue_fin['tax_rus'])
revenue_fin['revenue_type_eng'] = revenue_fin['revenue_type_eng'].fillna(revenue_fin['tax_eng'])
revenue_fin = revenue_fin.drop(['tax_rus', 'tax_eng'], axis=1)

# getting rid of some NaN values in population and income that appeared after appending the tax data
data_for_fill = revenue_fin.groupby(by=['year','region_eng'])[['population', 'real_income', 'income_per_cap', 'poverty', 'rub_usd']].min()
data_for_fill = data_for_fill.rename(columns={'population':'population_fill', 'real_income':'real_income_fill', 'income_per_cap':'income_per_cap_fill',
                                              'poverty':'poverty_fill', 'rub_usd':'rub_usd_fill'})

revenue_fin = revenue_fin.set_index(['year', 'region_eng']).join(data_for_fill).reset_index()
revenue_fin['population'] = revenue_fin['population'].fillna(revenue_fin['population_fill'])
revenue_fin['real_income'] = revenue_fin['real_income'].fillna(revenue_fin['real_income_fill'])
revenue_fin['income_per_cap'] = revenue_fin['income_per_cap'].fillna(revenue_fin['income_per_cap_fill'])
revenue_fin['poverty'] = revenue_fin['poverty'].fillna(revenue_fin['poverty_fill'])
revenue_fin['rub_usd'] = revenue_fin['rub_usd'].fillna(revenue_fin['rub_usd_fill'])
revenue_fin = revenue_fin.drop(['population_fill', 'real_income_fill', 'income_per_cap_fill', 'poverty_fill', 'rub_usd_fill'], axis=1)

# DATASET 7: FEDERAL BUDGET *************************************************************************************************************************************** 

# creating a dictionary with two tables for each year between 2011 and 2021:

path_dir = r"./budget_data/fed"

files = glob.glob(os.path.join(path_dir, "*.xlsx"))

budget_dict = dict()

budget_dict = []

for f in files:
    year = int(f[18:22]) 
        
    x= pd.read_excel(f, sheet_name=1)
    x['filename'] = f
    y= pd.read_excel(f, sheet_name=3)
    y['filename'] = f
            
    budget_dict.append([x, y])
    
# extracting the columns:

for index in [0,1,2,5,6,7,8,9]:
        
    inc = budget_dict[index][0] 
    spnd = budget_dict[index][1]
        
    inc = inc.applymap(lambda s: s.lower() if type(s) == str else s) 
    spnd = spnd.applymap(lambda s: s.lower() if type(s) == str else s)
        
    inc = inc.iloc[:, [0,2,3,4]]
    inc.columns = ['revenue_type_rus', 'revenue_id', 'revenue', 'year']
    inc['year'] = [x[18:22] for x in inc['year']] 
    
    budget_dict[index][0] = inc.dropna().reset_index(drop=True).drop(inc.index[0:4], axis=0).reset_index(drop=True)
        
    spnd = spnd.iloc[:, [0,2,3,4,5,8,10]]
    spnd.columns = ['spending_type_rus', 'spnd_id_1', 'spnd_id_2', 'spnd_id_3', 'spnd_id_4', 'spending', 'year']
    spnd['year'] = [x[18:22] for x in spnd['year']] 
    
    if index == 0:
        budget_dict[index][1] = spnd.drop([0,1,2,3,4,5,7], axis=0).reset_index(drop=True)
    else:
        budget_dict[index][1] = spnd.drop([0,1,2,3,4,6], axis=0).reset_index(drop=True)
    
# the 2021 Treasury dataframe is different from others (cumulative, not generalized report), so we'll handle it separately;
# I also use cumulative reports for for 2014-2015 dataframes that have missing rows for an unknown reason

for index in [3,4,10]:
    
    inc = budget_dict[index][0]
    spnd = budget_dict[index][1] 
    
    inc = inc.applymap(lambda s: s.lower() if type(s) == str else s)
    spnd = spnd.applymap(lambda s: s.lower() if type(s) == str else s)
    
    inc = inc.iloc[:, [0,3,5,9]]
    inc.columns = ['revenue_type_rus', 'revenue_id', 'revenue', 'year']
    inc['year'] = [x[18:22] for x in inc['year']] 
    
    budget_dict[index][0] = inc.dropna().reset_index(drop=True)  
    
    spnd = spnd.iloc[:, [0,2,3,4,5,7,9]]
    spnd.columns = ['spending_type_rus', 'spnd_id_1', 'spnd_id_2', 'spnd_id_3', 'spnd_id_4', 'spending', 'year']
    spnd['year'] = [x[18:22] for x in spnd['year']]
    
    budget_dict[index][1] = spnd.drop([0,1,2,3,4,6], axis=0).reset_index(drop=True)
    
# concatinating the dataframes:

df_list_rev = []
df_list_spnd = []
    
for index in range(len(budget_dict)):
        
    x = budget_dict[index][0]
    y = budget_dict[index][1]
        
    df_list_rev.append(x)
    df_list_spnd.append(y)
    
fed_rev = pd.concat(df_list_rev, ignore_index=True)
fed_spnd = pd.concat(df_list_spnd, ignore_index=True)

# fixing the data types:

fed_rev['revenue'] = fed_rev['revenue'].replace('\xa0', '', regex=True)
fed_rev['revenue'] = fed_rev['revenue'].replace(' ', '', regex=True)
fed_rev['revenue'] = fed_rev['revenue'].replace(',', '.', regex=True)
fed_rev['revenue'] = pd.to_numeric(fed_rev['revenue'])

fed_spnd['spending'] = fed_spnd['spending'].replace(',', '.', regex=True)
fed_spnd['spending'] = fed_spnd['spending'].replace(' ', '', regex=True)
fed_spnd['spending'] = fed_spnd['spending'].replace('\xa0', '', regex=True)
fed_spnd['spending'] = pd.to_numeric(fed_spnd['spending'])

fed_rev['revenue_id'] = fed_rev['revenue_id'].replace(' ', '', regex=True)
fed_rev['revenue_id'] = fed_rev['revenue_id'].replace('x', '00000000000000000', regex=True)

fed_rev['year'] = pd.to_numeric(fed_rev['year'])
fed_spnd['year'] = pd.to_numeric(fed_spnd['year'])

# in some dataframes it's an English 'x' in some it's a Russian 'x':
fed_spnd['spnd_id_1'] = fed_spnd['spnd_id_1'].replace('х', '0', regex=True)
fed_spnd['spnd_id_1'] = fed_spnd['spnd_id_1'].replace('x', '0', regex=True)
fed_spnd['spnd_id_2'] = fed_spnd['spnd_id_2'].replace('x', '0', regex=True)
fed_spnd['spnd_id_2'] = fed_spnd['spnd_id_2'].replace('х', '0', regex=True)
fed_spnd['spnd_id_3'] = fed_spnd['spnd_id_3'].replace('х', '0', regex=True)
fed_spnd['spnd_id_4'] = fed_spnd['spnd_id_4'].replace('х', '0', regex=True)
fed_spnd['spnd_id_3'] = fed_spnd['spnd_id_3'].replace('x', '0', regex=True)
fed_spnd['spnd_id_4'] = fed_spnd['spnd_id_4'].replace('x', '0', regex=True)

fed_spnd['spnd_id_4'] = fed_spnd['spnd_id_4'].astype('str')
fed_spnd['spnd_id_4'] = fed_spnd['spnd_id_4'].str.split('.').str[0]
fed_spnd['spnd_id_4'] = fed_spnd['spnd_id_4'].replace('nan', np.nan, regex=True)

fed_spnd['spnd_id_1'] = fed_spnd['spnd_id_1'].fillna(0)
fed_spnd['spnd_id_2'] = fed_spnd['spnd_id_2'].fillna(0)
fed_spnd['spnd_id_3'] = fed_spnd['spnd_id_3'].fillna(0)
fed_spnd['spnd_id_4'] = fed_spnd['spnd_id_4'].fillna(0)

fed_spnd['spnd_id_1'] = pd.to_numeric(fed_spnd['spnd_id_1']).astype('Int64')
fed_spnd['spnd_id_2'] = pd.to_numeric(fed_spnd['spnd_id_2']).astype('Int64')
fed_spnd['spnd_id_4'] = pd.to_numeric(fed_spnd['spnd_id_4']).astype('Int64')

fed_spnd['spnd_id_1'] = fed_spnd['spnd_id_1'].astype('int')
fed_spnd['spnd_id_2'] = fed_spnd['spnd_id_2'].astype('int')
fed_spnd['spnd_id_4'] = fed_spnd['spnd_id_4'].astype('int')

# appending English names of budget items:
codes_revenue_1 = revenue_fin.query(
    'revenue_id != "00000000000000000"')[['revenue_id', 'revenue_type_eng']].groupby(
    by=['revenue_id', 'revenue_type_eng']).min().reset_index()
codes_revenue = codes_revenue.rename(columns={'code':'revenue_id', 'revenue_indicator':'revenue_type_eng'})
codes_revenue = pd.concat([codes_revenue_1, codes_revenue], ignore_index=True).drop_duplicates().sort_values(by='revenue_id')


codes_spending['spending_indicator'] = codes_spending['spending_indicator'].str.lower()

fed_rev = fed_rev.set_index('revenue_id').join(codes_revenue.set_index('revenue_id'), how='left').reset_index()
fed_spnd = fed_spnd.set_index('spnd_id_2').join(
    codes_spending.rename(columns={'code':'spnd_id_2'}).set_index('spnd_id_2'), how='left').reset_index().rename(
    columns={'spending_indicator':'spending_type_eng'})

# getting rid of noise:

fed_spnd = fed_spnd[~fed_spnd['spending_type_rus'].isnull()]
fed_spnd = fed_spnd[~fed_spnd['spending_type_rus'].str.contains('дефицит/профицит')]
fed_spnd = fed_spnd[~fed_spnd['spending_type_rus'].str.contains('результат исполнения федерального бюджета')]

# CODIFICATION ****************************************************************************************************************************************************

# In this chunk, we'll extract subcodes from the unique transaction codes to ease future analysis.

# REGIONAL BUDGETS:

# extracting the subcodes
revenue_fin['r1'] = [x[:1] for x in revenue_fin['revenue_id']]
revenue_fin['r2'] = [x[1:3] for x in revenue_fin['revenue_id']]
revenue_fin['r3'] = [x[3:5] for x in revenue_fin['revenue_id']]
revenue_fin['r4'] = [x[5:8] for x in revenue_fin['revenue_id']]

# making them numeric to agregate data
revenue_fin['r1'] = pd.to_numeric(revenue_fin['r1']).astype('int')
revenue_fin['r2'] = pd.to_numeric(revenue_fin['r2']).astype('int')
revenue_fin['r3'] = pd.to_numeric(revenue_fin['r3']).astype('int')
revenue_fin['r4'] = pd.to_numeric(revenue_fin['r4']).astype('int')

# transforming the spending code to extract substrings
spending['spending_id_1'] = spending['spending_id_1'].astype('str')
spending['spending_id_1'] = spending['spending_id_1'].str.zfill(4)

# extracting subcodes and making them numeric
spending['s1'] = [x[:2] for x in spending['spending_id_1']]
spending['s2'] = [x[2:4] for x in spending['spending_id_1']]
spending['s1'] = pd.to_numeric(spending['s1']).astype('int')
spending['s2'] = pd.to_numeric(spending['s2']).astype('int')

spending['spending_id_1'] = pd.to_numeric(spending['spending_id_1']).astype('int')

# FEDERAL BUDGET:

fed_rev['r1'] = [x[:1] for x in fed_rev['revenue_id']]
fed_rev['r2'] = [x[1:3] for x in fed_rev['revenue_id']]
fed_rev['r3'] = [x[3:5] for x in fed_rev['revenue_id']]
fed_rev['r4'] = [x[5:8] for x in fed_rev['revenue_id']]

fed_rev['r1'] = pd.to_numeric(fed_rev['r1']).astype('int')
fed_rev['r2'] = pd.to_numeric(fed_rev['r2']).astype('int')
fed_rev['r3'] = pd.to_numeric(fed_rev['r3']).astype('int')
fed_rev['r4'] = pd.to_numeric(fed_rev['r4']).astype('int')

fed_spnd['spnd_id_2'] = fed_spnd['spnd_id_2'].astype('str')
fed_spnd['spnd_id_2'] = fed_spnd['spnd_id_2'].str.zfill(4)

fed_spnd['s1'] = [x[:2] for x in fed_spnd['spnd_id_2']]
fed_spnd['s2'] = [x[2:4] for x in fed_spnd['spnd_id_2']]
fed_spnd['s1'] = pd.to_numeric(fed_spnd['s1']).astype('int')
fed_spnd['s2'] = pd.to_numeric(fed_spnd['s2']).astype('int')

fed_spnd['spnd_id_2'] = pd.to_numeric(fed_spnd['spnd_id_2']).astype('int')

revenue_fin.to_csv('final_data/revenue.csv')
spending.to_csv('final_data/spending.csv')
fed_rev.to_csv('final_data/fed_rev.csv')
fed_spnd.to_csv('final_data/fed_spend.csv')

# CREATING A DATASET FOR ANALYSIS *********************************************************************************************************************************

fed_spnd['spnd_id_1'] = fed_spnd['spnd_id_1'].astype('int')

# COUNTRY DATA ----------------------------------------------------------------------------------------------------------------------------------------------------

# REGIONS/REVENUE

# Regional money flows: own revenues, taxes fo federation, transfers from federation
reg_revenue_1 = revenue_fin.query('(r1 in (0,1) & r2 == 0 & region_eng == "russia") | (r1 == 2 & r2 == 2 & r3 == 0 & region_eng == "russia")')[[
  'year', 'revenue_id', 'revenue', 'tax_to_fed']].reset_index(drop=True).set_index('year')
reg_revenue_1['revenue'] = reg_revenue_1['revenue'].fillna(reg_revenue_1['tax_to_fed'])
reg_revenue_1 = reg_revenue_1.drop('tax_to_fed', axis=1)
reg_revenue_1 = reg_revenue_1.reset_index().pivot(index='revenue_id', columns='year', values='revenue')

# no cumulative data for all Russia in 2011, so we count sums for regions and add them:
reg_revenue_1.loc['10000000000000000', 2011] = revenue_fin.query('year == 2011 & r1 == 1 & r2 == 0')['revenue'].sum()
reg_revenue_1.loc['20200000000000000', 2011] = revenue_fin.query('year == 2011 & r1 == 2 & r2 == 2 & r3 == 0')['revenue'].sum()
reg_revenue_1 = reg_revenue_1.rename(index={'00000000000000000':'tax_to_fed', '10000000000000000':'reg_own_revenue', '20200000000000000':'transfers_to_reg'})
reg_revenue_1['i2'] = 1 # 1 for regions 2 for federal budget
reg_revenue_1['i3'] = 1 # 1 for revenues 2 for spending
reg_revenue_1['r1'] = [3,1,2] # 1 for own revenues, 2 for transfers, 3 for federal tax
reg_revenue_1['r2'] = 0 # 1 for tax 2 for nontax own revenue
reg_revenue_1['r3'] = 0 # revenue subgroup
reg_revenue_1['r4'] = 0 # revenue item
reg_revenue_1['r5'] = 0 # revenue subitem
reg_revenue_1 = reg_revenue_1.reset_index()[['i2', 'i3', 'r1', 'r2', 'r3', 'r4', 'r5', 'revenue_id', 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 
                                             2021]].rename(columns={'revenue_id':'index'}).set_index(['i2', 'i3', 'r1', 'r2', 'r3', 'r4', 'r5',
                                                                                                      'index']).sort_index()

# Tax and non-tax revenues:
reg_revenue_2 = revenue_fin.query('r1 == 1 & 1 <= r2 <= 9 & r3 == 0 & year != 2011 & region_eng == "russia"')[['year', 'revenue']].groupby(by='year').sum()
reg_revenue_2 = reg_revenue_2.rename(columns={'revenue':'reg_tax_revenue'})
reg_revenue_2['reg_nontax_revenue'] = revenue_fin.query(
  'r1 == 1 & 10 <= r2 <= 19 & r3 == 0 & year != 2011 & region_eng == "russia"')[['year', 'revenue']].groupby(by='year').sum()
reg_revenue_2.loc[2011, 'reg_tax_revenue'] = revenue_fin.query('r1 == 1 & 1 <= r2 <= 9 & r3 == 0 & year == 2011 & region_eng != "russia"')['revenue'].sum()
reg_revenue_2.loc[2011, 'reg_nontax_revenue'] = revenue_fin.query('r1 == 1 & 10 <= r2 <= 19 & r3 == 0 & year == 2011 & region_eng != "russia"')['revenue'].sum()
reg_revenue_2 = reg_revenue_2.sort_index()
reg_revenue_2 = reg_revenue_2.T
reg_revenue_2['i2'] = 1 
reg_revenue_2['i3'] = 1 
reg_revenue_2['r1'] = 1 
reg_revenue_2['r2'] = [1,2] 
reg_revenue_2['r3'] = 0 
reg_revenue_2['r4'] = 0 
reg_revenue_2['r5'] = 0
reg_revenue_2 = reg_revenue_2.reset_index()[[
  'i2', 'i3', 'r1', 'r2', 'r3', 'r4', 'r5', 'index', 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021]].set_index([
  'i2', 'i3', 'r1', 'r2', 'r3', 'r4', 'r5', 'index']).sort_index()

# Revenue subgroups:
reg_revenue_3 = revenue_fin.query('r1 == 1 & r2 != 0 & r3 == 0 & region_eng == "russia"')[[
  'year', 'revenue_type_eng', 'revenue', 'r1', 'r2', 'r3', 'r4']].dropna().pivot(
  index=['r1', 'r2', 'r3', 'r4', 'revenue_type_eng'], columns='year', values='revenue')
reg_revenue_3[2011] = revenue_fin.query(
    'r1 == 1 & r2 != 0 & r3 == 0 & region_eng != "russia" & year == 2011')[[
    'year', 'region_eng', 'revenue_type_eng', 'revenue', 'r1', 'r2', 'r3', 'r4']].dropna().pivot_table(
    index=['r1', 'r2', 'r3', 'r4', 'revenue_type_eng'], columns='year', values='revenue', aggfunc='sum')[2011]
reg_revenue_3 = reg_revenue_3.reset_index()

# Revenue items:
reg_revenue_4 = revenue_fin.query(
    'r1 == 1 & r2 != 0 & r3 != 0 & r4 == 0 & region_eng == "russia"')[[
    'year', 'revenue_type_eng', 'revenue', 'r1', 'r2', 'r3', 'r4']].dropna().pivot(
    index=['r1', 'r2', 'r3', 'r4', 'revenue_type_eng'], columns='year', values='revenue')
reg_revenue_4[2011] = revenue_fin.query(
    'r1 == 1 & r2 != 0 & r3 != 0 & r4 == 0 & region_eng != "russia" & year == 2011')[[
    'year', 'region_eng', 'revenue_type_eng', 'revenue', 'r1', 'r2', 'r3', 'r4']].dropna().pivot_table(
    index=['r1', 'r2', 'r3', 'r4', 'revenue_type_eng'], columns='year', values='revenue', aggfunc='sum')[2011]
reg_revenue_4 = reg_revenue_4.reset_index()

# Revenue subitems:
reg_revenue_5 = revenue_fin.query(
    'r1 == 1 & r2 != 0 & r3 != 0 & r4 != 0 & region_eng == "russia"')[[
    'year', 'revenue_type_eng', 'revenue', 'r1', 'r2', 'r3', 'r4']].dropna().pivot(
    index=['r1', 'r2', 'r3', 'r4', 'revenue_type_eng'], columns='year', values='revenue')
reg_revenue_5[2011] = revenue_fin.query(
    'r1 == 1 & r2 != 0 & r3 != 0 & r4 != 0 & region_eng != "russia" & year == 2011')[[
    'year', 'region_eng', 'revenue_type_eng', 'revenue', 'r1', 'r2', 'r3', 'r4']].dropna().pivot_table(
    index=['r1', 'r2', 'r3', 'r4', 'revenue_type_eng'], columns='year', values='revenue', aggfunc='sum')[2011]
reg_revenue_5 = reg_revenue_5.reset_index()

reg_revenue_3 = pd.concat([reg_revenue_3, reg_revenue_4, reg_revenue_5])
reg_revenue_3['i2'] = 1
reg_revenue_3['i3'] = 1
reg_revenue_3 = reg_revenue_3.rename(columns={'r2':'r3', 'r3':'r4', 'r4':'r5'})
def set_id(s):
    if 1 <= s['r3'] <= 9:
        return 1
    elif 10 <= s['r3'] <= 19:
        return 2
reg_revenue_3['r2'] = reg_revenue_3.apply(set_id, axis=1)
reg_revenue_3 = reg_revenue_3.set_index(['i2', 'i3', 'r1', 'r2', 'r3', 'r4', 'r5', 'revenue_type_eng']).sort_index()
reg_revenue_3 = reg_revenue_3[[2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021]]

# Taxes to the federal center: total and by subgroups/items/subitems:
reg_revenue_6 = revenue_fin.query(
    'r1 != 0 & tax_to_fed == tax_to_fed & tax_to_fed != 0 & region_eng == "russia"')[[
    'year', 'revenue_type_eng', 'tax_to_fed', 'r1', 'r2', 'r3', 'r4']].dropna().pivot(
    index=['r1', 'r2', 'r3', 'r4', 'revenue_type_eng'], columns='year', values='tax_to_fed').reset_index()
reg_revenue_6['i2'] = 1
reg_revenue_6['i3'] = 1
reg_revenue_6['r1'] = 3
reg_revenue_6 = reg_revenue_6.rename(columns={'r2':'r3', 'r3':'r4', 'r4':'r5'})
reg_revenue_6['r2'] = 1
reg_revenue_6 = reg_revenue_6.set_index(['i2', 'i3', 'r1', 'r2', 'r3', 'r4', 'r5', 'revenue_type_eng']).sort_index()
reg_revenue_6 = reg_revenue_6[[2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021]]

# Concatinating all the data:
reg_revenue = pd.concat([reg_revenue_1, reg_revenue_2, reg_revenue_3, reg_revenue_6])

# REGIONS/SPENDING

# Total regional spendings
reg_spending_1 = spending.query('s1 == 0 & region_eng == "russia"')[[
    'year', 'spending']].reset_index(drop=True).set_index('year')
reg_spending_1 = reg_spending_1.rename(columns={'spending':'reg_spending'})
reg_spending_1.loc[2011, 'reg_spending'] = spending.query('year == 2011 & s1 == 0')['spending'].sum()
reg_spending_1 = reg_spending_1.sort_index().T
reg_spending_1['i2'] = 1 # 1 for regions 2 for federal budget
reg_spending_1['i3'] = 2 # 1 for revenues 2 for spending
reg_spending_1['s1'] = 0 # revenue section
reg_spending_1['s2'] = 0 # revenue subsection
reg_spending_1 = reg_spending_1.reset_index().set_index(['i2', 'i3', 's1', 's2', 'index'])

# Regional spendings - sections
reg_spending_2 = spending.query(
    'region_eng == "russia" & 1 <= s1 <= 14 & s2 == 0 & spending_id_2 == 0')[[
    'year', 'spending_type_eng', 'spending', 's1', 's2']].pivot(
    index=['s1', 's2', 'spending_type_eng'], columns='year', values='spending')
reg_spending_2[2011] = spending.query(
    'region_eng != "russia" & 1 <= s1 <= 14 & s2 == 0 & spending_id_2 == 0 & year == 2011')[[
    'year', 'spending_type_eng', 'spending', 's1', 's2']].pivot_table(
    index=['s1', 's2', 'spending_type_eng'], columns='year', values='spending', aggfunc='sum')
reg_spending_2 = reg_spending_2.reset_index()

# Regional spendings - subsections
reg_spending_3 = spending.query(
    'region_eng == "russia" & 1 <= s1 <= 14 & s2 != 0 & spending_id_2 == 0')[[
    'year', 'spending_type_eng', 'spending', 's1', 's2']].pivot(
    index=['s1', 's2', 'spending_type_eng'], columns='year', values='spending')
reg_spending_3[2011] = spending.query(
    'region_eng != "russia" & 1 <= s1 <= 14 & s2 != 0 & spending_id_2 == 0 & year == 2011')[[
    'year', 'spending_type_eng', 'spending', 's1', 's2']].pivot_table(
    index=['s1', 's2', 'spending_type_eng'], columns='year', values='spending', aggfunc='sum')
reg_spending_3 = reg_spending_3.reset_index()

reg_spending_2 = pd.concat([reg_spending_2, reg_spending_3])

reg_spending_2['i2'] = 1
reg_spending_2['i3'] = 2
reg_spending_2 = reg_spending_2.set_index(
    ['i2', 'i3', 's1', 's2', 'spending_type_eng'])[[2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021]]

reg_spending = pd.concat([reg_spending_1, reg_spending_2])

# FEDERAL/REVENUE

# Total federal revenues:
fed_revenue_1 = fed_rev.query('r1 == 1 & r2 == 0')[['year', 'revenue']].set_index('year')
fed_revenue_1 = fed_revenue_1.rename(columns={'revenue':'fed_revenue'})
fed_revenue_1['fed_tax_revenue'] = fed_rev.query(
    'r1 == 1 & 1 <= r2 <= 9 & r3 == 0')[['year', 'revenue_type_eng', 'revenue']].pivot_table(
    index='year', values='revenue', aggfunc='sum')
fed_revenue_1['fed_nontax_revenue'] = fed_rev.query(
    'r1 == 1 & 10 <= r2 <= 19 & r3 == 0')[['year', 'revenue_type_eng', 'revenue']].pivot_table(
    index='year', values='revenue', aggfunc='sum')
fed_revenue_1 = fed_revenue_1.T
fed_revenue_1['i2'] = 2 
fed_revenue_1['i3'] = 1 
fed_revenue_1['r1'] = 1 
fed_revenue_1['r2'] = [0,1,2] 
fed_revenue_1['r3'] = 0 
fed_revenue_1['r4'] = 0 
fed_revenue_1['r5'] = 0
fed_revenue_1 = fed_revenue_1.reset_index().set_index(['i2', 'i3', 'r1', 'r2', 'r3', 'r4', 'r5', 'index'])

# Federal revenues by subgroups/items/subitems:
fed_revenue_2 = fed_rev.dropna().query(
    'r1 == 1 & r2 != 0 & r3 == 0')[['year', 'revenue_type_eng', 'revenue', 'r1', 'r2', 'r3', 'r4']].pivot(
    index=['r1', 'r2', 'r3', 'r4', 'revenue_type_eng'], columns='year', values='revenue')
fed_revenue_3 = fed_rev.dropna().query(
    'r1 == 1 & r2 != 0 & r3 != 0 & r4 == 0')[['year', 'revenue_type_eng', 'revenue', 'r1', 'r2', 'r3', 'r4']].pivot(
    index=['r1', 'r2', 'r3', 'r4', 'revenue_type_eng'], columns='year', values='revenue')
fed_revenue_4 = fed_rev.dropna().query(
    'r1 == 1 & r2 != 0 & r3 != 0 & r4 != 0')[['year', 'revenue_type_eng', 'revenue', 'r1', 'r2', 'r3', 'r4']].pivot(
    index=['r1', 'r2', 'r3', 'r4', 'revenue_type_eng'], columns='year', values='revenue')
fed_revenue_2 = pd.concat([fed_revenue_2, fed_revenue_3, fed_revenue_4])

fed_revenue_2['i2'] = 2
fed_revenue_2['i3'] = 1
fed_revenue_2 = fed_revenue_2.reset_index().rename(columns={'r2':'r3', 'r3':'r4', 'r4':'r5'})
def set_id(s):
    if 1 <= s['r3'] <= 9:
        return 1
    elif 10 <= s['r3'] <= 19:
        return 2
fed_revenue_2['r2'] = fed_revenue_2.apply(set_id, axis=1)
fed_revenue_2 = fed_revenue_2.set_index(['i2', 'i3', 'r1', 'r2', 'r3', 'r4', 'r5', 'revenue_type_eng']).sort_index()
# Concatinating:
fed_revenue = pd.concat([fed_revenue_1, fed_revenue_2])

# FEDERAL/SPENDING

fed_spending_1 = fed_spnd.query('s1 == 0 & spnd_id_1 == 0')[['year', 'spending']].set_index('year')
fed_spending_1 = fed_spending_1.rename(columns = {'spending':'fed_spending'})
fed_spending_1 = fed_spending_1.T
fed_spending_1['i2'] = 2 # 1 for regions 2 for federal budget
fed_spending_1['i3'] = 2 # 1 for revenues 2 for spending
fed_spending_1['s1'] = 0 # revenue section
fed_spending_1['s2'] = 0 # revenue subsection
fed_spending_1 = fed_spending_1.reset_index().set_index(['i2', 'i3', 's1', 's2', 'index'])

fed_spending_2 = fed_spnd.query(
    's1 != 0 & s2 == 0 & spnd_id_1 != 0 & spnd_id_3 == 0')[['year', 'spending_type_eng', 'spending', 's1', 's2']].pivot_table(
    index=['s1', 's2', 'spending_type_eng'], columns='year', values='spending', aggfunc='sum')
fed_spending_3 = fed_spnd.query(
    's1 != 0 & s2 != 0 & spnd_id_1 != 0 & spnd_id_3 == 0')[['year', 'spending_type_eng', 'spending', 's1', 's2']].pivot_table(
    index=['s1', 's2', 'spending_type_eng'], columns='year', values='spending', aggfunc='sum')
fed_spending_2 = pd.concat([fed_spending_2, fed_spending_3])

fed_spending_2['i2'] = 2
fed_spending_2['i3'] = 2
fed_spending_2 = fed_spending_2.reset_index().set_index(['i2', 'i3', 's1', 's2', 'spending_type_eng'])

fed_spending = pd.concat([fed_spending_1, fed_spending_2])

df_russia = pd.concat([reg_revenue.reset_index(), reg_spending.reset_index(), fed_revenue.reset_index(),
                       fed_spending.reset_index()], axis=0).set_index(
    ['i2', 'i3', 'r1', 'r2', 'r3', 'r4', 'r5', 's1', 's2', 'index']).sort_index().reset_index()
df_russia = df_russia.fillna(0)
df_russia[['r1', 'r2', 'r3', 'r4', 'r5', 's1', 's2']] = df_russia[['r1', 'r2', 'r3', 'r4', 'r5', 's1', 's2']].astype('int')

add_data = revenue_fin.query('region_eng == "russia"')[[
    'year', 'population', 'real_income', 'income_per_cap', 'poverty', 'rub_usd']].groupby(by='year').min()
add_data.loc[2011, 'population'] = regions.query('region_eng == "Russia"')[2011].iloc[0]
add_data.loc[2011, 'real_income'] = real_income.query('region_eng == "Russia"')['2011'].iloc[0]
add_data.loc[2011, 'income_per_cap'] = income_percap.query('region_eng == "Russia"')['2011'].iloc[0]
add_data.loc[2011, 'poverty'] = poverty.query('region_eng == "Russia"')[2011].iloc[0]
add_data.loc[2011, 'rub_usd'] = rubusd.iloc[0,0]
add_data = add_data.T

add_data['i3'] = [5,6,7,8,9]
add_data[['i2','r1','r2','r3','r4','r5','s1','s2']] = 0
add_data = add_data[['i2','i3','r1','r2','r3','r4','r5','s1','s2',2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021]]

df_russia = pd.concat([df_russia, add_data.reset_index()], axis=0)
df_russia = df_russia.reset_index(drop=True)

df_russia['i1'] = 2
df_russia['region_eng'] = 'russia'
df_russia = df_russia[['i1','i2','i3','r1','r2','r3','r4','r5','s1','s2','index','region_eng',
                       2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021]]

# REGIONS DATA ----------------------------------------------------------------------------------------------------------------------------------------------------

# REVENUE

reg_revenue_1 = revenue_fin.query(
    '(r1 in (0,1) & r2 == 0 & region_eng != "russia") | (r1 == 2 & r2 == 2 & r3 == 0 & region_eng != "russia")')[[
    'year', 'revenue_id', 'region_eng', 'revenue', 'tax_to_fed']]
reg_revenue_1['revenue'] = reg_revenue_1['revenue'].fillna(reg_revenue_1['tax_to_fed'])
reg_revenue_1 = reg_revenue_1.drop('tax_to_fed', axis=1)
reg_revenue_1 = reg_revenue_1.reset_index(drop=True).pivot(
    index=['revenue_id', 'region_eng'], columns='year', values='revenue').reset_index()
reg_revenue_1['revenue_id'] = reg_revenue_1['revenue_id'].replace('00000000000000000', 'tax_to_fed', regex=True)
reg_revenue_1['revenue_id'] = reg_revenue_1['revenue_id'].replace('10000000000000000', 'reg_own_revenue', regex=True)
reg_revenue_1['revenue_id'] = reg_revenue_1['revenue_id'].replace('20200000000000000', 'transfers_to_reg', regex=True)
reg_revenue_1['i3'] = 1
def set_id(s):
    if s['revenue_id'] == 'reg_own_revenue':
        return 1
    elif s['revenue_id'] == 'transfers_to_reg':
        return 2
    elif s['revenue_id'] == 'tax_to_fed':
        return 3
reg_revenue_1['r1'] = reg_revenue_1.apply(set_id, axis=1)
reg_revenue_1['r3'] = 0
reg_revenue_1['r4'] = 0
reg_revenue_1['r5'] = 0
reg_revenue_1 = reg_revenue_1.set_index(['i3', 'r1', 'r3', 'r4', 'r5', 'revenue_id', 'region_eng'])

reg_revenue_2 = revenue_fin.query('r1 == 1 & r2 != 0 & r3 == 0 & region_eng != "russia"')[[
    'year', 'region_eng', 'r2', 'r3', 'r4', 'revenue_type_eng', 'revenue']].dropna()
reg_revenue_2['i3'] = 1
reg_revenue_2['r1'] = 1
reg_revenue_2 = reg_revenue_2.rename(columns={'r2':'r3', 'r3':'r4', 'r4':'r5', 'revenue_type_eng':'index'}).pivot(
    ['i3', 'r1', 'r3', 'r4', 'r5', 'index', 'region_eng'], columns='year', values='revenue')

reg_revenue_3 = revenue_fin.query('r1 == 1 & r2 != 0 & r3 == 0 & region_eng != "russia"')[[
    'year', 'region_eng', 'r2', 'r3', 'r4', 'revenue_type_eng', 'tax_to_fed']].dropna()
reg_revenue_3['i3'] = 1
reg_revenue_3['r1'] = 3
reg_revenue_3 = reg_revenue_3.rename(columns={'r2':'r3', 'r3':'r4', 'r4':'r5', 'revenue_type_eng':'index'}).pivot(
    ['i3', 'r1', 'r3', 'r4', 'r5', 'index', 'region_eng'], columns='year', values='tax_to_fed')

reg_revenue_4 = revenue_fin.query('r1 == 1 & r2 != 0 & r3 != 0 & r4 == 0 & region_eng != "russia"')[[
    'year', 'region_eng', 'r2', 'r3', 'r4', 'revenue_type_eng', 'revenue']].dropna()
reg_revenue_4['i3'] = 1
reg_revenue_4['r1'] = 1
reg_revenue_4 = reg_revenue_4.rename(columns={'r2':'r3', 'r3':'r4', 'r4':'r5', 'revenue_type_eng':'index'}).pivot(
    ['i3', 'r1', 'r3', 'r4', 'r5', 'index', 'region_eng'], columns='year', values='revenue')

reg_revenue_5 = revenue_fin.query('r1 == 1 & r2 != 0 & r3 != 0 & r4 == 0 & region_eng != "russia"')[[
    'year', 'region_eng', 'r2', 'r3', 'r4', 'revenue_type_eng', 'tax_to_fed']].dropna()
reg_revenue_5['i3'] = 1
reg_revenue_5['r1'] = 3
reg_revenue_5 = reg_revenue_5.rename(columns={'r2':'r3', 'r3':'r4', 'r4':'r5', 'revenue_type_eng':'index'}).pivot(
    ['i3', 'r1', 'r3', 'r4', 'r5', 'index', 'region_eng'], columns='year', values='tax_to_fed')

reg_revenue_6 = revenue_fin.query('r1 == 1 & r2 != 0 & r3 != 0 & r4 != 0 & region_eng != "russia"')[[
    'year', 'region_eng', 'r2', 'r3', 'r4', 'revenue_type_eng', 'revenue']].dropna()
reg_revenue_6['i3'] = 1
reg_revenue_6['r1'] = 1
reg_revenue_6 = reg_revenue_6.rename(columns={'r2':'r3', 'r3':'r4', 'r4':'r5', 'revenue_type_eng':'index'}).pivot(
    ['i3', 'r1', 'r3', 'r4', 'r5', 'index', 'region_eng'], columns='year', values='revenue')

reg_revenue_7 = revenue_fin.query('r1 == 1 & r2 != 0 & r3 != 0 & r4 != 0 & region_eng != "russia"')[[
    'year', 'region_eng', 'r2', 'r3', 'r4', 'revenue_type_eng', 'tax_to_fed']].dropna()
reg_revenue_7['i3'] = 1
reg_revenue_7['r1'] = 3
reg_revenue_7 = reg_revenue_7.rename(columns={'r2':'r3', 'r3':'r4', 'r4':'r5', 'revenue_type_eng':'index'}).pivot(
    ['i3', 'r1', 'r3', 'r4', 'r5', 'index', 'region_eng'], columns='year', values='tax_to_fed')

reg_revenue = pd.concat([reg_revenue_1, reg_revenue_2, reg_revenue_3, reg_revenue_4, reg_revenue_5, reg_revenue_6,
                         reg_revenue_7])
reg_revenue = reg_revenue.sort_index().reset_index()
reg_revenue = reg_revenue.rename(columns={'revenue_id':'index'})

# SPENDING 

reg_spending_1 = spending.query('s1 == 0 & region_eng != "russia"')[[
    'year', 'region_eng', 'spending']].reset_index(drop=True).pivot(index='region_eng', columns='year', values='spending')
reg_spending_1['index'] = 'reg_spending'
reg_spending_1['i3'] = 2
reg_spending_1['s1'] = 0
reg_spending_1['s2'] = 0

reg_spending_1 = reg_spending_1.reset_index().set_index(['i3', 's1', 's2', 'index', 'region_eng'])

reg_spending_2 = spending.query(
    's1 != 0 & s2 == 0 & region_eng != "russia"')[[
    'year', 'region_eng', 's1', 's2', 'spending_type_eng', 'spending']].reset_index(drop=True).pivot(
    index=['s1', 's2', 'spending_type_eng', 'region_eng'], columns='year', values='spending').reset_index()

reg_spending_3 = spending.query('s1 != 0 & s2 != 0 & spending_id_2 == 0 & region_eng != "russia"')[[
    'year', 'region_eng', 's1', 's2', 'spending_type_eng', 'spending']].reset_index(
    drop=True).pivot(index=['s1', 's2', 'spending_type_eng', 'region_eng'], columns='year', values='spending').reset_index()

reg_spending_3 = reg_spending_3[reg_spending_3['spending_type_eng'].notna()]
reg_spending_2 = pd.concat([reg_spending_2, reg_spending_3])
reg_spending_2['i3'] = 2
reg_spending_2 = reg_spending_2.rename(columns={'spending_type_eng':'index'}).set_index(['i3', 's1', 's2', 'index', 'region_eng'])

reg_spending = pd.concat([reg_spending_1, reg_spending_2])

# CONCATINATING

df_regions = pd.concat([reg_revenue, reg_spending.reset_index()], axis=0).set_index(['i3', 'r1', 'r3', 'r4', 'r5', 's1', 's2', 'index']).sort_index().reset_index()
df_regions = df_regions.fillna(0)
df_regions[['r1', 'r3', 'r4', 'r5', 's1', 's2']] = df_regions[['r1', 'r3', 'r4', 'r5', 's1', 's2']].astype('int')

add_data = revenue_fin.query('region_eng != "russia"')[['year', 'region_eng', 'population', 'real_income', 'income_per_cap', 
                                                        'poverty', 'rub_usd']].groupby(by=['year', 'region_eng']).min()
add_data_pivot = pd.melt(add_data.reset_index(), id_vars=['year', 'region_eng'], 
                         value_vars=['population', 'real_income', 'income_per_cap', 'poverty', 'rub_usd'], 
                         var_name='index').pivot(index=['index', 'region_eng'], columns='year', values='value').reset_index()

def set_id(s):
    if s['index'] == "population":
        return 5
    elif s['index'] == "real_income":
        return 6
    elif s['index'] == "income_per_cap":
        return 7
    elif s['index'] == "poverty":
        return 8
    elif s['index'] == "rub_usd":
        return 9
add_data_pivot['i3'] = add_data_pivot.apply(set_id, axis=1)
add_data_pivot[['r1','r3','r4','r5','s1','s2']] = 0

df_regions = pd.concat([df_regions, add_data_pivot], axis=0)
df_regions = df_regions.reset_index(drop=True)

df_regions['i1'] = 1
df_regions['i2'] = 1
def set_id(s):
    if 1 <= s['r3'] <= 9:
        return 1
    elif 10 <= s['r3'] <= 19:
        return 2
    else:
        return 0
df_regions['r2'] = df_regions.apply(set_id, axis=1)

df_regions = df_regions[['i1','i2','i3','r1','r2','r3','r4','r5','s1','s2','index','region_eng', 2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021]]

budget_data = pd.concat([df_russia, df_regions], axis=0)

budget_data = pd.melt(budget_data, id_vars=['i1','i2','i3','r1','r2','r3','r4','r5','s1','s2','index','region_eng'],
                      value_vars=[2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021], var_name='year')

budget_data.to_csv('final_data/russian_budget_data.csv')
