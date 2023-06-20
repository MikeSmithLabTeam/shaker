path = "C:\\Users\ppyol1\Documents\shaker\Motor_Positions.txt"


with open(path, "w") as file:
    write_data=file.write("2,2\n")

with open(path) as file:
    read_data=file.read()

read_data = read_data.split(",")
print(read_data[0])
