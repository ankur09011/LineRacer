from helpers import get_intersection
from lineobject import LineObject

line1 = {"slope" : 5,
         "intcpt" : 2}

line2 = {"slope" : 3,
         "intcpt" : 8}



print(get_intersection(line1, line2))
