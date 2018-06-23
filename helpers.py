def get_intersection(first_line, second_line):
    """
    lines:
        y = mx + b
        y = nx + c

    We set them equal and solve for x:
        mx + b = nx + c
        mx - nx = c - b
        (m-n)x = c - b
        x = (c - b) / (m-n)

    :param first_line:
    :param second_line:
    :return:

    """
    if parallel(first_line, second_line):
        return False

    m = first_line.get("slope", 0)
    n = second_line.get("slope", 0)

    b = first_line.get("intcpt", 0)
    c = second_line.get("intcpt", 0)

    x = (c - b) / (m - n)

    y = (m * x) + b

    return (x,y)


def parallel(first_line, second_line):
    """

    if two slopes are equal lines are parallel

    :param first_slope:
    :param second_slope:
    :return:
    """
    m = first_line.get("slope", 0)
    n = second_line.get("slope", 0)

    if (m - n) == 0 :
        return True
    else:
        return False


def solve_for_y(x, line):
    '''
    Solve for Y cord using line equation
    :param x:
    :param slope:
    :param yintercept:
    :return:
    '''
    slope = line.get("slope")
    yintercept = line.get("intcpt")

    if slope != None and yintercept != None:
            return float(slope) * x + float(yintercept)
    else:
            raise Exception('Can not solve on a vertical line')