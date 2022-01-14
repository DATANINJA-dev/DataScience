import pandasgui
import pandas as pd
from pyspark.sql import SparkSession
from sort_by_product_coverage import order_product_coverage, order_product_coverage_pandas
from datetime import datetime


def show_dataframe_gui(df):
    pandasgui.show(df, block=False)


def elapsed_time(start_time, message):
    end_time = datetime.now()
    print(message, ' --> ', end_time - start_time)
    return end_time


if __name__ == '__main__':
    start_time = datetime.now()

    source_file = 'LLISTAT EXCEL PRODUCTORS ECOLOGICS.xlsx'
    method = 'pandas'  # 'spark'

    # Read and clean product information
    product_cols = [('TIPOLOGIA GENERAL DE PRODUCTE', 'CATEGORIA'),
                    ('TIPOLOGIA ESPECÍFICA DE PRODUCTE', 'PRODUCTE'),
                    ('ÁREA GEOGRÀFICA', 'ZONA'),
                    ('LOCALITAT', 'LOCALITAT'),
                    ('NOM DE CONTACTE', 'CONTACTE'),
                    ('NOM DE L\'EMPRESA', 'EMPRESA'),
                    ('EMAIL DE CONTACTE', 'MAIL')]
    product_list_pd = pd.read_excel(source_file, 'Hoja1',
                                    usecols=[x[0] for x in product_cols])
    for col in product_cols:
        product_list_pd = product_list_pd.rename({col[0]: col[1]}, axis='columns')

    # Read and clean ponderations
    ponderation_pd = pd.read_excel(source_file, 'Hoja2')
    ponderation_pd = ponderation_pd.fillna(value=1)

    # Get list of required products
    required_products = [x.strip() for x in ponderation_pd.drop_duplicates(['PRODUCTE'])['PRODUCTE'].tolist()]
    order_product_coverage_pandas(product_list_pd, ponderation_pd, required_products)

    # Process data in PySpark and prepare for final selection
    if method == 'spark':
        spark = SparkSession.builder.getOrCreate()
    else:
        spark = None

    providers_list = order_product_coverage(method, product_list_pd, ponderation_pd, required_products, spark)
    intermediate_time = elapsed_time(start_time, 'First processing')

    # Compute CUMULATIVE_COVERAGE
    df = pd.DataFrame(columns=providers_list.columns.values)

    nrow, ncol = df.shape
    df.loc[nrow] = providers_list.iloc[0]  # copy first row

    cumulative_products = df.iloc[nrow, df.columns.get_loc('COVERED_PRODUCTS')]
    cumulative_products.sort()
    df['CUMULATIVE_COVERAGE'] = [cumulative_products]
    remaining_products = list(set(required_products).difference(cumulative_products))

    count = 0
    while len(remaining_products) > 0:
        remaining_providers = order_product_coverage(method, product_list_pd, ponderation_pd, remaining_products, spark)

        nrow, ncol = df.shape
        df.loc[nrow] = remaining_providers.iloc[0]

        cumulative_products = cumulative_products + df.iloc[nrow, df.columns.get_loc('COVERED_PRODUCTS')]
        cumulative_products.sort()
        df.at[nrow, 'CUMULATIVE_COVERAGE'] = cumulative_products
        remaining_products = list(set(required_products).difference(cumulative_products))

        intermediate_time = elapsed_time(intermediate_time, f'Iteration {count}')
        count = count + 1

    df.to_excel('selected_providers_' + method + '.xlsx')
    elapsed_time(start_time, 'Total elapsed time')
    # input("Press Enter to escape...")
