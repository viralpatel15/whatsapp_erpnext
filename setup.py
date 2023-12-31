from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in whatsapp_erpnext/__init__.py
from whatsapp_erpnext import __version__ as version

setup(
	name="whatsapp_erpnext",
	version=version,
	description="WhatsApp integration with ERPNext",
	author="Finbyz Tech Pvt. Ltd.",
	author_email="info@finbyz.tech",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
