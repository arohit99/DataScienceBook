#!/usr/bin/env python
# coding: utf-8

# # Building Delta lake using Spark

# This notebook has been run on [databricks community edition](https://community.cloud.databricks.com/). It details the data engineering process to load data, create delta tables and enrich data using spark. In a business scenario, we typically have external data sources such as azure data lake, aws s3 buckets mounted to databricks workspace. More information on it [here](https://docs.databricks.com/data/data-sources/azure/adls-gen2/azure-datalake-gen2-sp-access.html). We will be manually loading a dataset and go through the steps listed above.

# In[1]:


from pyspark.sql.types import IntegerType,BooleanType,DateType,StringType
import pyspark.sql.functions as F
from pyspark.sql.functions import col, when
from pyspark.sql.window import Window

spark.sql("set spark.sql.legacy.timeParserPolicy=LEGACY")


# ## Delta tables

# In[ ]:


# File location and type
file_location = "/FileStore/tables/data.csv"
file_type = "csv"

# CSV options
infer_schema = "true"
first_row_is_header = "true"
delimiter = ","

# The applied options are for CSV files. For other file types, these will be ignored.
df = spark.read.format(file_type)   .option("inferSchema", infer_schema)   .option("header", first_row_is_header)   .option("sep", delimiter)   .load(file_location)

display(df)


# In[ ]:


print('shape of the dataset ({},{})'.format(df.count(),len(df.columns)))


# Ok, now we have dataset loaded into workspace. Lets persist it as a delta table and create a table object so that we can query it using sql

# In[ ]:


( df
    .write
    .format('delta')
    .mode('overwrite')
    .save('/bronze/raw_data')
)


# In[ ]:


get_ipython().run_line_magic('fs', 'ls')


# In[ ]:


get_ipython().run_line_magic('fs', 'ls /bronze/raw_data/')


# In[ ]:


spark.sql("CREATE DATABASE IF NOT EXISTS db ") 


# In[ ]:


spark.sql('''
CREATE TABLE db.raw_data
  USING DELTA 
  LOCATION '/bronze/raw_data'
''')


# In[ ]:


get_ipython().run_line_magic('sql', 'select * from db.raw_data')


# We managed to load csv files, convert them into delta format and persist them in a database. We shall now perform data transformations to enrich data and prepare datasets which can be used for data analysis.

# ## ETL Process

# In[ ]:


transactions = spark.sql('''select * from db.raw_data ''')


# In[ ]:


transactions = transactions.withColumn('InvoiceDate', F.from_unixtime(F.unix_timestamp(col('InvoiceDate'),'MM/dd/yyyy HH:mm'),'yyyyMMdd'))                   .withColumn('CustomerId', col('CustomerId').cast(StringType())) 

w = Window().partitionBy('InvoiceNo')
transactions = transactions.withColumn('ItemCost', F.round(col('Quantity')*col('UnitPrice'),2))                            .withColumn('InvoiceItems', F.size(F.collect_set('StockCode').over(w)))                            .withColumn('InvoiceCost', F.sum('ItemCost').over(w))


# In[ ]:


display(transactions)


# In[ ]:


( transactions
    .write
    .format('delta')
    .mode('overwrite')
    .partitionBy('InvoiceDate')
    .save('/silver/transactions')
)

spark.sql('''CREATE TABLE db.transactions
  USING DELTA 
  LOCATION '/silver/transactions' ''')


# In[ ]:


get_ipython().run_line_magic('sql', '')
select * from db.transactions


# We have successfully completed ETL process and cleaned the dataset. We are now ready to dive into data analysis.
