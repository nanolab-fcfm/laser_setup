from Scripts.utils import *
path_to_file = r"C:\Users\nanol\nanolab\laser_setup\data\2023-09-07\IVg2023-09-07_9.csv"
data = read_pymeasure(path_to_file)
dp = find_dp(data)
print(dp)