path = "C:\\Users\ppyol1\Documents\shaker\Motor_Positions.txt"

x,y= 432,33
string= str(x)+","+str(y)

with open(path, "w") as file:
    write_data_x=file.write(string)

with open(path) as file:
    read_data=file.read()

read_data = read_data.split(",")
y_d = int(read_data[1])

print(read_data[0])
print(y_d)
print(type(y_d))
