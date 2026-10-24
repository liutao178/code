import json
import os
import shutil
import time
import random
from cloakbrowser import launch_persistent_context


class Scraper:
	# Seconds to wait for an element to appear
	wait_element_time = 5

	profiles_folder = 'profiles'
	profile_name = 'facebook'

	def __init__(self, url):
		self.url = url
		self.context = None
		self.page = None
		self.profile_dir = os.path.abspath(os.path.join(self.profiles_folder, self.profile_name))
		# Must check before setup_driver creates the folder
		self.profile_existed = os.path.isdir(self.profile_dir) and bool(os.listdir(self.profile_dir))
		self.setup_driver()

	def setup_driver(self):
		if self.context:
			self.context.close()
			self.context = None
			self.page = None

		os.makedirs(self.profile_dir, exist_ok=True)

		launch_kwargs = {
			'headless': True,
			'humanize': True,
			'locale': 'en-US',
			'viewport': None,
			'args': [
				'--start-maximized',
				'--disable-notifications',
				'--lang=en-US',
				'--disable-quic',
			],
		}

		# Optional: set PROXY_URL=http://user:pass@host:port (often required to reach Facebook)
		proxy = os.environ.get('PROXY_URL') or os.environ.get('HTTPS_PROXY') or os.environ.get('HTTP_PROXY')
		if proxy:
			launch_kwargs['proxy'] = proxy
			launch_kwargs['geoip'] = True
			print('Using proxy: ' + proxy.split('@')[-1])

		self.context = launch_persistent_context(self.profile_dir, **launch_kwargs)
		self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
		self._goto(self.url)

	def __del__(self):
		try:
			self.close()
		except Exception:
			pass

	def close(self):
		if self.context:
			try:
				self.context.close()
			except Exception:
				pass
			self.context = None
			self.page = None

	def delete_profile(self):
		"""Close browser and remove the persistent profile directory."""
		self.close()
		if os.path.isdir(self.profile_dir):
			shutil.rmtree(self.profile_dir, ignore_errors=True)
			print('Deleted profile because cookie login failed: ' + self.profile_dir)

	def add_login_functionality(self, login_url, is_logged_in_selector, cookies_file_name='fb.json'):
		"""Reuse existing profile session when possible; otherwise inject fb.json cookies.

		On failure, delete profiles/facebook so the next run starts clean.
		"""
		self.login_url = login_url
		self.is_logged_in_selector = is_logged_in_selector

		cookies_path = cookies_file_name
		if not os.path.isabs(cookies_path) and not os.path.exists(cookies_path):
			if not cookies_path.endswith('.json'):
				cookies_path = cookies_path + '.json'

		# self.go_to_page(login_url)

		# Profile already has saved session — skip re-injecting cookies
		if self.profile_existed:
			if self.is_logged_in(30):
				print('Logged in using existing profile: ' + self.profile_dir)
				return
			print('Existing profile is not logged in, will inject cookies from ' + cookies_path)

		if not os.path.exists(cookies_path):
			print('ERROR: Cookie file not found: ' + cookies_path)
			exit()

		self.load_cookies(cookies_path)
		self.go_to_page(login_url)

		if self.is_logged_in(30):
			return

		print('ERROR: Login with cookies failed. Please update ' + cookies_path + ' and try again.')
		self.delete_profile()
		exit()

	def load_cookies(self, cookies_path):
		with open(cookies_path, encoding='utf-8') as cookies_file:
			raw_cookies = json.load(cookies_file)

		playwright_cookies = []
		for cookie in raw_cookies:
			item = {
				'name': cookie['name'],
				'value': cookie['value'],
				'domain': cookie.get('domain', '.facebook.com'),
				'path': cookie.get('path', '/'),
				'httpOnly': bool(cookie.get('httpOnly', False)),
				'secure': bool(cookie.get('secure', True)),
			}

			if not cookie.get('session') and cookie.get('expirationDate') is not None:
				item['expires'] = int(cookie['expirationDate'])

			same_site = cookie.get('sameSite')
			if same_site is not None:
				same_site_lower = str(same_site).lower()
				if same_site_lower in ('no_restriction', 'none'):
					item['sameSite'] = 'None'
				elif same_site_lower == 'lax':
					item['sameSite'] = 'Lax'
				elif same_site_lower == 'strict':
					item['sameSite'] = 'Strict'

			playwright_cookies.append(item)

		self.context.add_cookies(playwright_cookies)

	def is_logged_in(self, wait_element_time=None):
		if wait_element_time is None:
			wait_element_time = self.wait_element_time
		return self.find_element(self.is_logged_in_selector, False, wait_element_time)

	def wait_random_time(self):
		random_sleep_seconds = round(random.uniform(0.20, 1.20), 2)
		time.sleep(3)

	def go_to_page(self, page):
		self.wait_random_time()
		self._goto(page)

	def _goto(self, url, wait_until='domcontentloaded', retries=3):
		"""Navigate with retries. Prefer www.facebook.com when given bare facebook.com."""
		if not url:
			raise ValueError('go_to_page/ _goto requires a non-empty url')

		candidates = [url]
		if '://www.facebook.com' not in url and '://facebook.com' in url:
			candidates.append(url.replace('://facebook.com', '://www.facebook.com', 1))

		last_error = None
		for attempt in range(retries):
			for candidate in candidates:
				try:
					self.page.goto(candidate, wait_until=wait_until, timeout=60000)
					return
				except Exception as error:
					last_error = error
					print(f'Navigation failed ({attempt + 1}/{retries}): {candidate} -> {error}')
					time.sleep(1.5)

		print(
			'ERROR: Cannot open page after retries.\n'
			'If Facebook is blocked, set a proxy, e.g.:\n'
			'  set PROXY_URL=http://127.0.0.1:7890\n'
			'  python main.py'
		)
		raise last_error

	def _locator(self, selector):
		return self.page.locator(selector).first

	def _locator_xpath(self, xpath):
		return self.page.locator(f'xpath={xpath}').first

	def find_element(self, selector, exit_on_missing_element=True, wait_element_time=None):
		if wait_element_time is None:
			wait_element_time = self.wait_element_time

		locator = self._locator(selector)
		try:
			locator.wait_for(state='visible', timeout=wait_element_time * 1000)
		except Exception:
			if exit_on_missing_element:
				print('ERROR: Timed out waiting for the element with css selector "' + selector + '" to load')
				exit()
			return False

		return locator

	def find_element_by_xpath(self, xpath, exit_on_missing_element=True, wait_element_time=None):
		if wait_element_time is None:
			wait_element_time = self.wait_element_time

		locator = self._locator_xpath(xpath)
		try:
			locator.wait_for(state='visible', timeout=wait_element_time * 1000)
		except Exception:
			if exit_on_missing_element:
				print('ERROR: Timed out waiting for the element with xpath "' + xpath + '" to load')
				exit()
			return False

		return locator

	def element_click(self, selector, delay=True, exit_on_missing_element=True, force=False):
		if delay:
			self.wait_random_time()

		element = self.find_element(selector, exit_on_missing_element)
		if not element:
			return

		self._click_locator(element, force=force)

	def element_click_by_xpath(self, xpath, delay=True, exit_on_missing_element=True, force=False):
		if delay:
			self.wait_random_time()

		element = self.find_element_by_xpath(xpath, exit_on_missing_element)
		if not element:
			return

		self._click_locator(element, force=force)

	def press_key(self, key, times=1):
		"""Press a keyboard key one or more times (e.g. ArrowDown, Enter)."""
		for _ in range(times):
			time.sleep(0.15)
			self.page.keyboard.press(key)

	def _click_locator(self, element, force=False):
		"""Click with fallbacks — helps when ::before/::after overlays block the target."""
		timeout = self.wait_element_time * 1000
		try:
			element.click(timeout=timeout, force=force)
			return
		except Exception:
			pass

		try:
			element.click(timeout=timeout, force=True)
			return
		except Exception:
			pass

		# Last resort: click the element (or its option parent) via JS
		element.evaluate(
			'''el => {
				const option = el.closest('[role="option"], [role="menuitem"], [role="menuitemradio"]') || el;
				option.click();
			}'''
		)

	def element_send_keys(self, selector, text, delay=True, exit_on_missing_element=True):
		if delay:
			self.wait_random_time()

		element = self.find_element(selector, exit_on_missing_element)
		if not element:
			return

		element.click(timeout=self.wait_element_time * 1000)
		element.fill(str(text))

	def element_send_keys_by_xpath(self, xpath, text, delay=True, exit_on_missing_element=True):
		if delay:
			self.wait_random_time()

		element = self.find_element_by_xpath(xpath, exit_on_missing_element)
		if not element:
			return

		element.click(timeout=self.wait_element_time * 1000)
		element.fill(str(text))

	def input_file_add_files(self, selector, files):
		locator = self._locator(selector)
		try:
			locator.wait_for(state='attached', timeout=self.wait_element_time * 1000)
		except Exception:
			print('ERROR: Timed out waiting for the input_file with selector "' + selector + '" to load')
			exit()

		self.wait_random_time()

		# Accept Selenium-style "\n"-joined paths or a list
		if isinstance(files, str):
			file_list = [os.path.normpath(p.strip()) for p in files.split('\n') if p.strip()]
		else:
			file_list = [os.path.normpath(p) for p in files]

		missing = [p for p in file_list if not os.path.exists(p)]
		if missing:
			print('ERROR: Exiting from the program! Please check if these file paths are correct:\n' + '\n'.join(missing))
			exit()

		locator.set_input_files(file_list)

	def element_clear(self, selector, delay=True, exit_on_missing_element=True):
		if delay:
			self.wait_random_time()

		element = self.find_element(selector, exit_on_missing_element)
		if not element:
			return

		element.fill('')

	def element_delete_text(self, selector, delay=True, exit_on_missing_element=True):
		if delay:
			self.wait_random_time()

		element = self.find_element(selector, exit_on_missing_element)
		if not element:
			return

		element.fill('')

	def element_wait_to_be_invisible(self, selector):
		locator = self._locator(selector)
		try:
			locator.wait_for(state='hidden', timeout=self.wait_element_time * 1000)
		except Exception:
			print('Warning when waiting the element with selector "' + selector + '" to be invisible')

	def element_wait_to_be_invisible_by_xpath(self, xpath):
		locator = self._locator_xpath(xpath)
		try:
			locator.wait_for(state='hidden', timeout=self.wait_element_time * 1000)
		except Exception:
			print('Warning when waiting the element with xpath "' + xpath + '" to be invisible')

	def scroll_to_element(self, selector, exit_on_missing_element=True):
		element = self.find_element(selector, exit_on_missing_element)
		if not element:
			return
		element.scroll_into_view_if_needed()

	def scroll_to_element_by_xpath(self, xpath, exit_on_missing_element=True):
		element = self.find_element_by_xpath(xpath, exit_on_missing_element)
		if not element:
			return
		element.scroll_into_view_if_needed()
