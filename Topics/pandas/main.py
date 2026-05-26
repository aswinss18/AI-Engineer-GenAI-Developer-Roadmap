import pandas as pd

data = {
    "name": ["Aswin", "Rahul", "Arun"],
    "salary": [50000, 70000, 45000]
}

# df1 = pd.DataFrame(data)

# df2 = pd.read_csv("timesheet.csv")

df=pd.read_json("posts.json")

# filteredData = df2[df2["Available"] > 100]

# print(df1,"Framed Data")

print("JSON Data Info:", len(df), "records found.")