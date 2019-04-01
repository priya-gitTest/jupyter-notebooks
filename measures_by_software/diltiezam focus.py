# ---
# jupyter:
#   jupytext_format_version: '1.2'
#   kernelspec:
#     display_name: Python (jupyter virtualenv)
#     language: python
#     name: jupyter
#   language_info:
#     codemirror_mode:
#       name: ipython
#       version: 3
#     file_extension: .py
#     mimetype: text/x-python
#     name: python
#     nbconvert_exporter: python
#     pygments_lexer: ipython3
#     version: 3.6.5
# ---

from ebmdatalab.bq import cached_read
import matplotlib.pyplot as plt
import pandas as pd

vendors = pd.read_csv('vendors.csv')
# Clean up the input data
vendors['Principal Supplier'] = vendors['Principal Supplier'].str.strip()
vendors.loc[vendors['Principal Supplier'] == 'INPS', 'Principal Supplier'] = 'Vision'  # seems they changed in 2017
vendors = vendors.loc[vendors['Date'] > '2016-02-01']  # there is some dirty data ("Unknowns") before this

# +
from ebmdatalab import bq
import importlib
importlib.reload(bq)
measures = ['diltiazem']

def get_data(measure_id):
    sql = """
SELECT
  TRIM(Principal_Supplier) AS supplier,
  m.practice_id,
  m.pct_id,
  m.month,
  numerator,
  denominator,
  '{measure_id}' AS measure_id
FROM
  measures.practice_data_{measure_id} m
JOIN
  hscic.vendors software
ON
  software.ODS = practice_id
  AND Date = m.month
JOIN
  hscic.practices
ON
  practices.code = software.ODS
JOIN
  hscic.practice_statistics
ON
  practice_statistics.practice = practices.code
  AND Date = DATE(practice_statistics.month)
WHERE
  practices.setting = 4
  AND total_list_size > 100
  AND practices.status_code = 'A'
  AND denominator > 0
ORDER BY
  month""".format(measure_id=measure_id)
    import pandas as pd
    df = bq.cached_read(sql, csv_path="data/diltiazem.csv.zip".format(measure_id))
    return df


df = get_data('diltiazem')
# -

df['calc_value'] = df['numerator'] / df['denominator']
df['month'] = pd.to_datetime(df['month'])


df.groupby(['month', 'supplier']).mean()['calc_value'].unstack().plot.line()
plt.legend(loc='best')
plt.title("diltiazem measure, mean values per supplier")

df.rename(columns={'pct_id':'pct'}, inplace=True)  # The CCG column must be named 'pct' for the maps function
by_pct = df.groupby('pct').sum().reset_index()
by_pct['calc_value'] = by_pct['numerator'] / by_pct['denominator']
by_supplier_and_pct = df.groupby(['supplier', 'pct']).sum().reset_index()
by_supplier_and_pct['calc_value'] = by_supplier_and_pct['numerator'] / by_supplier_and_pct['denominator']

# + {"scrolled": false}
from ebmdatalab import charts
import matplotlib.gridspec as gridspec
from ebmdatalab import maps
import importlib
importlib.reload(maps)

plt.figure(figsize=(12,8))
layout = gridspec.GridSpec(2, 2)
left_ax = plt.subplot(layout[0, 0])
right_subplot = layout[0:2, 1]



charts.deciles_chart(
        df,
        period_column='month',
        column='calc_value',
        title="Diltiazem measure nationally",
        ylabel="proportion",
        show_outer_percentiles=True,
        show_legend=False,
    ax=left_ax
    )
maps.ccg_map(by_pct, title="Diltiazem measure (all suppliers)", 
             column='calc_value', cartogram=True,
             show_legend=False,
             subplot_spec=right_subplot)

plt.show()

# + {"scrolled": false}


plt.figure(figsize=(20,30))
layout = gridspec.GridSpec(8, 4)
for i, supplier in enumerate(['EMIS', 'TPP', 'Microtest', 'Vision']):
    left_ax = plt.subplot(layout[i * 2, 0])
    right_subplot = layout[(i * 2):(i * 2 + 2), 1]
    #print("right subplot layout[%s]" % (2 - i % 2))
    #print("left ax layout[%s:%s, 0]" % ((i * 2), (i * 2 + 2)))
    #continue
    charts.deciles_chart(
        df[df['supplier'] == supplier],
        period_column='month',
        column='calc_value',
        title="Diltiazem measure for {}".format(supplier),
        ylabel="proportion",
        show_outer_percentiles=True,
        show_legend=False,
        ax=left_ax
    )
    left_ax.set_ylim([0, 1])
    maps.ccg_map(
        by_supplier_and_pct[by_supplier_and_pct['supplier'] == supplier], 
        column='calc_value', 
        show_legend=False,
        cartogram=True, 
        subplot_spec=right_subplot)
plt.show()
