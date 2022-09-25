The project contains a synthesized dataset on the Russian federal and regional budget totals, items, and subitems, as well as a number of key economic indicators
such as the population, real income, income per capita, and poverty level for the years 2011–2021, aggregated on the regional and country level.

It is aimed to make the data easier to analyze for non-professionals in economics, namely, for journalists (like me).

There are three notebooks in the repository, where all the steps of the dataset creation are explained, and where it is used to analyze the budget data, visualize it
(with Matplotlib, Seaborn, and Plotly), and create an interactive dashboard tracking the key economic indicators (in Plotly Dash).

<b>The dataset</b>

> final_data/russian_budget_data.csv - The dataset is detailed down to the level of budget subitems.

<b>The codes include:</b>

GENERAL CODES:

<b>i1</b>: the level of aggregation

> <b>1</b> = the region

> <b>2</b> = the whole country

 <b>i2</b>: the type of budget

> <b>1</b> = regional

> <b>2</b> = federal

<b>i3</b>: the type of indicator 

> <b>1</b> = revenue

> <b>2</b> = spending

> <b>5</b> = population

> <b>6</b> = real income

> <b>7</b> = income per capita

> <b>8</b> = poverty level

> <b>9</b> = yearly USDRUB exchange rate

REVENUE CODES:

<b>r1</b>: revenue group

> <b>1</b> = own revenues

> <b>2</b> = federal transfers to regions

> <b>3</b> = regional taxes to the federal budget

<b>r2</b>: revenue type (for own revenues and federal taxes) 

> <b>1</b> = tax

> <b>2</b> = nontax

<b>r3</b>: revenue subgroup

<b>r4</b>: revenue item

<b>r5</b>: revenue subitem

SPENDING CODES:

<b>s1</b>: spending section

<b>s2</b>: spending subsection

<b>The columns include:</b>

> <b>year</b> - the year between 2011 and 2021

> <b>region_eng</b> - the name of the region (+Russia for the country level) (eng)

> <b>index</b> - the name of the indicator (eng)

> <b>value</b> - the amount/quantity/percentage/value

<b>All the data is given in rubles</b> by default; there's a USDRUB indicator to convert it into dollars by the corresponding year's exchange rate (according to the
Russian Central Bank).

<b>The notebooks</b>

> <b>Data wrangling</b>: explains the entire dataframe construction process.

> <b>Data analysis</b>, where the dataset is used to explore and visualize the budget data

> <b>The dashboard</b>, where the indicators-tracking dashboard is created and explained

<b>Additional datasets</b>

There are also four intermediate datasets with more detailed information for 2011–2021 (the programs, subprograms, etc. inside the revenue and spending subitems
and subsections), but this additional data is not translated into English and is differently structured. All four datasets can be useful in case there's a need
to explore a budget item further:

> final_data/revenue.csv - the regional revenues;

> final_data/spending.csv - the regional spendings;

> final_data/fed_rev.csv - the federal revenues;

> final_data/fed_spend.csv - the federal spendings.

<b>The limitations to this project</b>

> This is a test project with data only for the years 2011–2021 and no cumulative monthly data. It is possible to append to it in the future, using the same code.

> There's no possibility to update the dataset at the moment because Russian officials have stopped publishing information on budget spending while there is a war
in Ukraine.
