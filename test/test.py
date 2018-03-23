import csv

coll = {}
columns = [ 'Order name', 'Attendee name' ]
collected_columns = []

def quote (string):
    return '"' + string + '"'

with open('checkin.csv') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        #print(row)

        order_code = row['Order code']
        attendee = row['Attendee name']
        product = row['Product']
        paid = row['Paid']

        # Product will be our new column header name
        if product not in collected_columns:
            collected_columns.append(product)

        # Check whether we need to modify an existing order (that's the only unique code here)
        new_row = {}
        if attendee in coll:
            new_row = coll[attendee]

        new_row['order_code'] = order_code

        if 'products' not in new_row:
            new_row['products'] = {}

        #new_row['products'][product] = "Paid: " + paid # don't store true/false, if this field is set with the paid status, it will be printed
        new_row['products'][product] = "yes"

        coll[attendee] = new_row

header = ';'.join(quote(x) for x in columns + collected_columns)

print(header)

#print("Collected Columns: ")
#print(collected_columns)

separator = ','

for attendee, row in coll.items():
    line = []
    line.append(row['order_code'])
    line.append(attendee)

#    print(row)

    for c in collected_columns:
        if c in row['products']:
            line.append(row['products'][c])
        else:
            line.append('') # empty value

    new_row = ','.join(quote(x) for x in line)
    print(new_row)


