from helpers import get_intersection, solve_for_y, distance

line1 = {"slope" : 5.5,
         "intcpt" : 2}

line2 = {"slope" : 3,
         "intcpt" : 8}



x_intersection, y_intersection = get_intersection(line1, line2)

print(x_intersection, y_intersection)

x1 = x_intersection
x2 = x_intersection

flag_too_far = False
too_far_distance = 10.0


while not flag_too_far:
    x1 = x1 + 1
    y1 = solve_for_y(x1, line1)
    x2 = x2 + 1
    y2 = solve_for_y(x2, line2)

    dis = distance(x1,y1,x2,y2)

    print(f'first line --> {x1,y1}')
    print(f'second line --> {x2,y2}')
    print(f'distance --> {dis}')

    if dis > too_far_distance:
        flag_too_far = True