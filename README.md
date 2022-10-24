# Russian Budget Tracker

The project contains a synthesized dataset on the Russian federal and regional budget totals, items, and subitems, as well as a number of key economic indicators
such as the population, real income, income per capita, and poverty level for the years 2011–2021, aggregated on the regional and country level. 

This is an attempt to make the data easier to analyze for non-professionals in economics, namely, for journalists.

### Notebooks

There are two notebooks in the repository, where all the steps of the dataset creation are explained, and where it is used to analyze the budget data and visualize it (with Matplotlib, Seaborn, and Plotly). Below are the links to view them on [NBViewer](https://nbviewer.org/), with all the widgets, working hyperlinks, and all my comments:

> The [Data Wrangling](https://nbviewer.org/github/lomska/russian-budget-tracker/blob/main/rbt_data_wrangling.ipynb) notebook explains the entire dataframe construction process step-by-step. This notebook corresponds to the [rbt_data_wrangling.py](rbt_data_wrangling.py) doc from the repository, the execution of which takes about 15 minutes. 

> In the [Data Analysis](https://nbviewer.org/github/lomska/russian-budget-tracker/blob/main/rbt_data_analysis.ipynb) notebook, I use the dataset to explore and visualize the budget data. 

### Dashboard

This project's indicators-tracking dashboard (in Plotly Dash) is available [HERE](https://russian-budget-tracker.herokuapp.com/). There's only a desktop version available at the moment. The code from [rbt_tracking_dashboard_local_server.py](rbt_tracking_dashboard_local_server.py) shows how to run it locally; the assets folder is necessary for that.

### Dataset

> [final_data/russian_budget_data.csv](final_data/russian_budget_data.csv) - The dataset is detailed down to the level of budget subitems

#### Codes for the dataset

| Code Type | Index | Code Group | Value | Meaning |
| --- | --- | --- | --- | --- |
| General | i1 | The Aggregation Level | 1 | region |
| General | i1 | The Aggregation Level | 2 | country |
| General | i2 | Budget Type | 1 | regional |
| General | i2 | Budget Type | 2 | federal |
| General | i3 | Indicator | 1 | revenue |
| General | i3 | Indicator | 2 | spending | 
| General | i3 | Indicator | 5 | population |
| General | i3 | Indicator | 6 | real income |
| General | i3 | Indicator | 7 | income per capita |
| General | i3 | Indicator | 8 | poverty level |
| General | i3 | Indicator | 9 | USDRUB exchange rate |
| Revenue | r1 | Revenue Group | 1 | own revenues |
| Revenue | r1 | Revenue Group | 2 | federal transfers to regions |
| Revenue | r1 | Revenue Group | 3 | regional taxes to the federal budget |
| Revenue | r2 | Revenue Type | 1 | tax |
| Revenue | r2 | Revenue Type | 2 | nontax |
| Revenue | r3 | Revenue Subgroup | 1-18 | See [revenue subgroup, item, and subitem codes (.xlsx)](revenue_codes_for_the_dataset.xlsx) |
| Revenue | r4 | Revenue Item | 1-11 | See [revenue subgroup, item, and subitem codes (.xlsx)](revenue_codes_for_the_dataset.xlsx) |
| Revenue | r5 | Revenue Subitem | 10-260 | See [revenue subgroup, item, and subitem codes (.xlsx)](revenue_codes_for_the_dataset.xlsx) |
| Spending | s1 | Spending Section | 1-14 | See [spending section and subsection codes (.xlsx)](spending_codes_for_the_dataset.xlsx) |
| Spending | s2 | Spending Subsection | 1-14 | See [spending section and subsection codes (.xlsx)](spending_codes_for_the_dataset.xlsx) |

<b>All the data is given in rubles</b> by default; there's a USDRUB indicator to convert it into dollars by the corresponding year's exchange rate (according to the
Russian Central Bank).

### Additional data

There are also four intermediate datasets with more detailed information for 2011–2021 (the programs, subprograms, etc. inside the revenue and spending subitems
and subsections), but this additional data is not translated into English and is differently structured. All four datasets can be useful in case there's a need
to explore a particular budget item further:

> [final_data/revenue.csv](final_data/revenue.csv) - the regional revenues;

> [final_data/spending.csv](final_data/spending.csv) - the regional spendings;

> [final_data/fed_rev.csv](final_data/fed_rev.csv) - the federal revenues;

> [final_data/fed_spend.csv](final_data/fed_spend.csv) - the federal spendings.

### Limitations to this project

> This is a test project with data only for the years 2011–2021 and no cumulative monthly data. The cumulative data is possible to append in the future, using the same code.

> There's no possibility (hopefully, temporarily) to update the dataset at the moment because Russian officials have stopped publishing information on regional budget spending while there is a war in Ukraine.
