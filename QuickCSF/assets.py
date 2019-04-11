import pkg_resources

def locate(resource):
	print('Mapping', resource, 'to', pkg_resources.resource_filename(__name__, 'assets/' + resource))
	return pkg_resources.resource_filename(__name__, 'assets/' + resource)
