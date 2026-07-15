# Goal: Automates a common ERP workflow in Odoo — log in, create a CRM lead, and verify it in the pipeline.
#
# Odoo is an open-source ERP with web modules for CRM, Sales, Inventory, Accounting, etc.
# By default this runs against Odoo's public demo instance (it resets regularly, so it is safe to write to).
# To run it against your own Odoo instance, set:
#   export ODOO_URL="https://mycompany.odoo.com"
#   export ODOO_USERNAME="admin@mycompany.com"
#   export ODOO_PASSWORD="your-password"
#
# Credentials are passed via `sensitive_data`, so the LLM only ever sees the
# x_odoo_username / x_odoo_password placeholders, never the real values.
# `allowed_domains` locks the agent to the ERP host so credentials can't leak elsewhere.

import asyncio
import os
import sys
from urllib.parse import urlparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

load_dotenv()

from browser_use import Agent, Browser, ChatBrowserUse

ODOO_URL = os.getenv('ODOO_URL', 'https://demo.odoo.com')
ODOO_USERNAME = os.getenv('ODOO_USERNAME', 'admin')
ODOO_PASSWORD = os.getenv('ODOO_PASSWORD', 'admin')

# Lock the agent to the ERP host (the public demo redirects between *.odoo.com subdomains).
odoo_host = urlparse(ODOO_URL).netloc
allowed_domains = ['*.odoo.com'] if odoo_host.endswith('odoo.com') else [odoo_host]

# Domain-scoped credentials: only injected on the Odoo host, filtered out of all LLM input.
sensitive_data: dict[str, str | dict[str, str]] = {
	f'https://{domain}': {
		'x_odoo_username': ODOO_USERNAME,
		'x_odoo_password': ODOO_PASSWORD,
	}
	for domain in allowed_domains
}

task = f"""
You are operating an Odoo ERP instance.

1. Go to {ODOO_URL}
2. If a login page is shown, sign in with username x_odoo_username and password x_odoo_password.
   (If you are already logged in, continue.)
3. Open the CRM app from the main apps menu.
4. Create a new lead/opportunity in the pipeline with:
   - Opportunity name: "Browser-Use Pilot Project"
   - Customer / company name: "Browser Use GmbH"
   - Expected revenue: 25000
5. Save it and confirm it now appears in the "New" stage of the pipeline.
6. Report back: the name of the created opportunity and the total number of
   opportunities currently visible in the "New" stage.
"""


async def main():
	browser = Browser(allowed_domains=allowed_domains)

	agent = Agent(
		task=task,
		llm=ChatBrowserUse(model='bu-2-0'),
		browser=browser,
		sensitive_data=sensitive_data,
	)

	history = await agent.run(max_steps=50)
	print(history.final_result())


if __name__ == '__main__':
	asyncio.run(main())
