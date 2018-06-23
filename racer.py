from helpers import get_intersection, solve_for_y
from lineobject import LineObject

line1 = {"slope" : 5,
         "intcpt" : 2}

line2 = {"slope" : 3,
         "intcpt" : 8}



x_intersection, y_intersection = get_intersection(line1, line2)

print(x_intersection, y_intersection)

x = x_intersection
for i in range(1, 10):
    print(f'current {i}')
    x = x + 1
    y = solve_for_y(x, line1)

    print(x,y)
