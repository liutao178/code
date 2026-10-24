import os


def update_listings(listings, type, scraper):
	# If listings are empty stop the function
	if not listings:
		return

	for listing in listings:
		# Publish the listing in marketplace
		isPublished = publish_listing(listing, type, scraper)

		# If the listing is not published from the first time, try again
		if not isPublished:
			publish_listing(listing, type, scraper)

def publish_listing(data, listing_type, scraper):
	# Choose listing type
	scraper.go_to_page('https://www.facebook.com/marketplace/create/' + listing_type)

	# Create string that contains all of the image paths separeted by \n
	images_path = generate_multiple_images_path(data['Photos Folder'], data['Photos Names'])
	# Add images to the the listing
	scraper.input_file_add_files('input[accept="image/*,image/heif,image/heic"]', images_path)

	# Add specific fields based on the listing_type
	function_name = 'add_fields_for_' + listing_type
	# Call function by name dynamically
	globals()[function_name](data, scraper)
	
	scraper.element_send_keys_by_xpath('//span[text()="Price"]/following-sibling::input[1]', data['Price'])
	scraper.element_send_keys_by_xpath('//span[text()="Description"]/following-sibling::div/textarea', data['Description'])
	scraper.element_send_keys_by_xpath('//span[text()="Location"]/following-sibling::input[1]', data['Location'])
	scraper.element_click('ul[role="listbox"] li:first-child > div')

	next_button_selector = 'div [aria-label="Next"] > div'
	next_button = scraper.find_element(next_button_selector, False, 3)
	if next_button:
		# Go to the next step
		scraper.element_click(next_button_selector)
		# Add listing to multiple groups
		# add_listing_to_multiple_groups(data, scraper)
	
	close_button_selector = '//span[text()="Close"]'
	close_button = scraper.find_element_by_xpath(close_button_selector, False, 10)
	if close_button:
		scraper.element_click_by_xpath(close_button_selector)
		scraper.go_to_page('https://www.facebook.com/marketplace/you/selling')
		return False

	# Publish the listing
	scraper.element_click('div[aria-label="Publish"]:not([aria-disabled])')

	leave_page_selector = '//div[@tabindex="0"] //span[text()="Leave Page"]'
	leave_page = scraper.find_element_by_xpath(leave_page_selector, False, 15)
	if leave_page:
		scraper.element_click_by_xpath(leave_page_selector)

	# Wait until the listing is published
	wait_until_listing_is_published(listing_type, scraper)

	if not next_button:
		post_listing_to_multiple_groups(data, listing_type, scraper)
	
	return True


def generate_multiple_images_path(path, images):
	# Resolve Photos Folder relative to project root (absolute paths still allowed)
	project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	folder = path.strip()
	if not os.path.isabs(folder):
		folder = os.path.join(project_root, folder)
	folder = os.path.normpath(folder)

	image_names = images.split(';')
	paths = []

	for image_name in image_names:
		image_name = image_name.strip()
		if image_name:
			paths.append(os.path.normpath(os.path.join(folder, image_name)))

	return '\n'.join(paths)

# Add specific fields for listing from type item
def add_fields_for_item(data, scraper):
	scraper.element_send_keys_by_xpath('//span[text()="Title"]/following-sibling::input[1]', data['Title'])

	# Scroll to "Category" select field
	scraper.scroll_to_element_by_xpath('//span[text()="Category"]')
	# Expand category select
	scraper.element_click_by_xpath('//span[text()="Category"]')
	# Select category
	scraper.element_click_by_xpath('//span[text()="' + data['Category'] + '"]')

	# Expand Condition, then ArrowDown to the matching option and press Enter
	scraper.element_click_by_xpath('//span[text()="Condition"]')
	select_condition_with_keyboard(data['Condition'], scraper)

# Facebook Marketplace Condition options in dropdown order
CONDITION_OPTIONS = [
	'New',
	'Used - Like New',
	'Used - Good',
	'Used - Fair',
]

def select_condition_with_keyboard(condition, scraper):
	"""Match data['Condition'] to dropdown order, ArrowDown that many times, then Enter."""
	normalized = condition.strip().lower().replace('–', '-').replace('—', '-')
	index = None
	for i, option in enumerate(CONDITION_OPTIONS):
		if option.lower() == normalized:
			index = i
			break

	if index is None:
		print(
			'ERROR: Unknown Condition "' + condition + '". '
			'Expected one of: ' + ', '.join(CONDITION_OPTIONS)
		)
		exit()

	# First ArrowDown focuses the first option (New), then move index more times
	scraper.press_key('ArrowDown', times=index + 1)
	scraper.press_key('Enter')

def generate_title_for_listing_type(data, listing_type):
	return data['Title']

def wait_until_listing_is_published(listing_type, scraper):
	scraper.element_wait_to_be_invisible_by_xpath('//h1[text()="Item for sale"]')
