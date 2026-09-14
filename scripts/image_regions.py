"""Named fixed regions in decoded image pixels; shared by scan and comparison."""
from PIL import ImageChops, ImageStat


def parse_regions(values, size):
    regions = []
    names = set()
    for value in values or []:
        try:
            name, coords = value.split(':', 1)
            box = [int(v) for v in coords.split(',')]
        except (ValueError, AttributeError) as exc:
            raise ValueError('Region format: name:left,top,right,bottom') from exc
        if not name or name in names or len(box) != 4:
            raise ValueError('Regions need unique names and four coordinates')
        left, top, right, bottom = box
        if not (0 <= left < right <= size[0] and 0 <= top < bottom <= size[1]):
            raise ValueError(f'Region {name} is outside image dimensions {size}')
        names.add(name)
        regions.append({'name': name, 'box': box})
    return regions


def difference_metrics(a, b, threshold=12):
    difference = ImageChops.difference(a.convert('RGB'), b.convert('RGB'))
    r, g, blue = difference.split()
    maximum = ImageChops.lighter(ImageChops.lighter(r, g), blue)
    histogram = maximum.histogram()
    return difference, {'mean_absolute_channel_error': sum(ImageStat.Stat(difference).mean) / 3,
        'changed_fraction': sum(histogram[threshold:]) / (a.width * a.height),
        'pixel_threshold': threshold}
