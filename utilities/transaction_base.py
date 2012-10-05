# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes.utils import load_json, cint, cstr, flt, get_defaults
from webnotes.model.doc import Document, addchild, getchildren
from webnotes.model.utils import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint

class TransactionBase:

	# Get Customer Default Primary Address - first load
	# -----------------------
	def get_default_customer_address(self, args=''):
		address_text, address_name = self.get_address_text(customer=self.doc.customer)
		contact_text, contact_name, contact_email, contact_mobile = self.get_contact_text(customer=self.doc.customer)
		self.doc.customer_address = address_name or ''
		self.doc.contact_person = contact_name or ''
		self.doc.address_display = address_text or ''
		self.doc.contact_display = contact_text or ''
		self.doc.contact_email = contact_email or ''
		self.doc.contact_mobile = contact_mobile or ''

		if args != 'onload':
			self.get_customer_details(self.doc.customer)
			self.get_sales_person(self.doc.customer)
		
	# Get Customer Default Shipping Address - first load
	# -----------------------
	def get_default_customer_shipping_address(self, args=''):		
		address_text, address_name = self.get_address_text(customer=self.doc.customer,is_shipping_address=1)
		contact_text, contact_name, contact_email, contact_mobile = self.get_contact_text(customer=self.doc.customer)		
		self.doc.customer_address = address_name or ''
		self.doc.contact_person = contact_name or ''
		self.doc.address_display = address_text or ''
		self.doc.contact_display = contact_text or ''
		self.doc.contact_email = contact_email or ''
		self.doc.contact_mobile = contact_mobile or ''
		
		if self.doc.doctype != 'Quotation' and args != 'onload':
			self.get_customer_details(self.doc.customer)
			self.get_sales_person(self.doc.customer)			

	# Get Customer Address
	# -----------------------
	def get_customer_address(self, args):
		args = load_json(args)		
		address_text, address_name = self.get_address_text(address_name=args['address'])
		contact_text, contact_name, contact_email, contact_mobile = self.get_contact_text(contact_name=args['contact'])
		ret = {
			'customer_address' : address_name,
			'contact_person' : contact_name,
			'address_display' : address_text,
			'contact_display' : contact_text,
			'contact_email' : contact_email,
			'contact_mobile' : contact_mobile
		}
		return ret	
			
	# Get Address Text
	# -----------------------
	def get_address_text(self, customer=None, address_name=None, supplier=None, is_shipping_address=None):
		if customer:
			cond = customer and 'customer="%s"' % customer or 'name="%s"' % address_name
		elif supplier:
			cond = supplier and 'supplier="%s"' % supplier or 'name="%s"' % address_name	
		else:
			cond = 'name="%s"' % address_name	

		if is_shipping_address:
			details = webnotes.conn.sql("select name, address_line1, address_line2, city, country, pincode, state, phone, fax from `tabAddress` where %s and docstatus != 2 order by is_shipping_address desc, is_primary_address desc limit 1" % cond, as_dict = 1)
		else:
			details = webnotes.conn.sql("select name, address_line1, address_line2, city, country, pincode, state, phone, fax from `tabAddress` where %s and docstatus != 2 order by is_primary_address desc limit 1" % cond, as_dict = 1)
		
		extract = lambda x: details and details[0] and details[0].get(x,'') or ''
		address_fields = [('','address_line1'),('\n','address_line2'),('\n','city'),(' ','pincode'),('\n','state'),('\n','country'),('\nPhone: ','phone'),('\nFax: ', 'fax')]
		address_display = ''.join([a[0]+extract(a[1]) for a in address_fields if extract(a[1])])
		if address_display.startswith('\n'): address_display = address_display[1:]		

		address_name = details and details[0]['name'] or ''
		return address_display, address_name

	# Get Contact Text
	# -----------------------
	def get_contact_text(self, customer=None, contact_name=None, supplier=None):
		if customer:
			cond = customer and 'customer="%s"' % customer or 'name="%s"' % contact_name
		elif supplier:
			cond = supplier and 'supplier="%s"' % supplier or 'name="%s"' % contact_name
		else:
			cond = 'name="%s"' % contact_name			
			
		details = webnotes.conn.sql("select name, first_name, last_name, email_id, phone, mobile_no, department, designation from `tabContact` where %s and docstatus != 2 order by is_primary_contact desc limit 1" % cond, as_dict = 1)

		extract = lambda x: details and details[0] and details[0].get(x,'') or ''
		contact_fields = [('','first_name'),(' ','last_name')]
		contact_display = ''.join([a[0]+cstr(extract(a[1])) for a in contact_fields if extract(a[1])])
		if contact_display.startswith('\n'): contact_display = contact_display[1:]
		
		contact_name = details and details[0]['name'] or ''
		contact_email = details and details[0]['email_id'] or ''
		contact_mobile = details and details[0]['mobile_no'] or ''
		return contact_display, contact_name, contact_email, contact_mobile

	def get_customer_details(self, name):
		"""
			Get customer details like name, group, territory
			and other such defaults
		"""
		customer_details = webnotes.conn.sql("""\
			select
				customer_name, customer_group, territory,
				default_sales_partner, default_commission_rate, default_currency,
				default_price_list
			from `tabCustomer`
			where name = %s and docstatus < 2""", name, as_dict=1)
		if customer_details:
			for f in ['customer_name', 'customer_group', 'territory']:
				self.doc.fields[f] = customer_details[0][f] or self.doc.fields.get(f)
			
			# fields prepended with default in Customer doctype
			for f in ['sales_partner', 'commission_rate', 'currency']:
				self.doc.fields[f] = customer_details[0]["default_%s" % f] or self.doc.fields.get(f)
			
			# optionally fetch default price list from Customer Group
			self.doc.price_list_name = (customer_details[0]['default_price_list']
				or webnotes.conn.get_value('Customer Group', self.doc.customer_group,
					'default_price_list')
				or self.doc.fields.get('price_list_name'))

	# Get Customer Shipping Address
	# -----------------------
	def get_shipping_address(self, name):
		details = webnotes.conn.sql("select name, address_line1, address_line2, city, country, pincode, state, phone from `tabAddress` where customer = '%s' and docstatus != 2 order by is_shipping_address desc, is_primary_address desc limit 1" %(name), as_dict = 1)
		
		extract = lambda x: details and details[0] and details[0].get(x,'') or ''
		address_fields = [('','address_line1'),('\n','address_line2'),('\n','city'),(' ','pincode'),('\n','state'),('\n','country'),('\nPhone: ','phone')]
		address_display = ''.join([a[0]+extract(a[1]) for a in address_fields if extract(a[1])])
		if address_display.startswith('\n'): address_display = address_display[1:]
		
		ret = {
			'shipping_address_name' : details and details[0]['name'] or '',
			'shipping_address' : address_display
		}
		return ret
		
	# Get Lead Details
	# -----------------------
	def get_lead_details(self, name):		
		details = webnotes.conn.sql("select name, lead_name, address_line1, address_line2, city, country, state, pincode, territory, contact_no, mobile_no, email_id, company_name from `tabLead` where name = '%s'" %(name), as_dict = 1)		
		
		extract = lambda x: details and details[0] and details[0].get(x,'') or ''
		address_fields = [('','address_line1'),('\n','address_line2'),('\n','city'),(' ','pincode'),('\n','state'),('\n','country'),('\nPhone: ','contact_no')]
		address_display = ''.join([a[0]+extract(a[1]) for a in address_fields if extract(a[1])])
		if address_display.startswith('\n'): address_display = address_display[1:]
		
		ret = {
			'lead_name' : extract('lead_name'),
			'address_display' : address_display,
			'territory' : extract('territory'),
			'contact_mobile' : extract('mobile_no'),
			'contact_email' : extract('email_id'),
			'organization' : extract('company_name')
		}
		return ret
		
		
	# Get Supplier Default Primary Address - first load
	# -----------------------
	def get_default_supplier_address(self, args):
		args = load_json(args)
		address_text, address_name = self.get_address_text(supplier=args['supplier'])
		contact_text, contact_name, contact_email, contact_mobile = self.get_contact_text(supplier=args['supplier'])
		ret = {
			'supplier_address' : address_name,
			'address_display' : address_text,
			'contact_person' : contact_name,
			'contact_display' : contact_text,
			'contact_email' : contact_email,
			'contact_mobile' : contact_mobile						
		}
		ret.update(self.get_supplier_details(args['supplier']))
		return ret
		
	# Get Supplier Address
	# -----------------------
	def get_supplier_address(self, args):
		args = load_json(args)
		address_text, address_name = self.get_address_text(address_name=args['address'])
		contact_text, contact_name, contact_email, contact_mobile = self.get_contact_text(contact_name=args['contact'])
		ret = {
			'supplier_address' : address_name,
			'address_display' : address_text,
			'contact_person' : contact_name,
			'contact_display' : contact_text,
			'contact_email' : contact_email,
			'contact_mobile' : contact_mobile
		}
		return ret
	
	# Get Supplier Details
	# -----------------------
	def get_supplier_details(self, name):
		supplier_details = webnotes.conn.sql("""\
			select supplier_name, default_currency
			from `tabSupplier`
			where name = %s and docstatus < 2""", name, as_dict=1)
		if supplier_details:
			return {
				'supplier_name': (supplier_details[0]['supplier_name']
					or self.doc.fields.get('supplier_name')),
				'currency': (supplier_details[0]['default_currency']
					or self.doc.fields.get('currency')),
			}
		else:
			return {}
		
	# Get Sales Person Details of Customer
	# ------------------------------------
	def get_sales_person(self, name):			
		self.doclist = self.doc.clear_table(self.doclist,'sales_team')
		idx = 0
		for d in webnotes.conn.sql("select sales_person, allocated_percentage, allocated_amount, incentives from `tabSales Team` where parent = '%s'" % name):
			ch = addchild(self.doc, 'sales_team', 'Sales Team', 1, self.doclist)
			ch.sales_person = d and cstr(d[0]) or ''
			ch.allocated_percentage = d and flt(d[1]) or 0
			ch.allocated_amount = d and flt(d[2]) or 0
			ch.incentives = d and flt(d[3]) or 0
			ch.idx = idx
			idx += 1
			
	# Get Company Specific Default Currency
	# -------------------------------------
	def get_company_currency(self, name):
		ret = webnotes.conn.sql("select default_currency from tabCompany where name = '%s'" %(name))
		dcc = ret and ret[0][0] or get_defaults()['currency']						
		return dcc	
	

	def get_formatted_message(self, args):
		""" get formatted message for auto notification"""
		return get_obj('Notification Control').get_formatted_message(args)
