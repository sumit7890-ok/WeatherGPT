"""
High-Speed In-Memory Geospatial Knowledge Base
Provides instant (<1ms) geocoding resolution for all Indian States, Union Territories,
major Indian cities and districts, and top world cities and capitals.
Prevents external network latency and DNS/SSL handshake timeouts for common search queries.
"""

from typing import List, Dict, Any, Optional
from backend.app.schemas import LocationSearchItem

# Pre-indexed comprehensive geospatial directory
# Format: name, formattedAddress, lat, lon, country, state, district, city, locality, aliases
_GEO_DATA: List[Dict[str, Any]] = [
    # ----------------------------------------------------
    # 1. Indian States & Union Territories
    # ----------------------------------------------------
    {
        "name": "Jharkhand",
        "formattedAddress": "Jharkhand, India",
        "latitude": 23.6102,
        "longitude": 85.2799,
        "country": "India",
        "state": "Jharkhand",
        "district": "Ranchi",
        "city": "Ranchi",
        "locality": "Jharkhand",
        "aliases": ["jharkhand", "jhar", "jharkand", "ranchi state"]
    },
    {
        "name": "Uttar Pradesh",
        "formattedAddress": "Uttar Pradesh, India",
        "latitude": 26.8467,
        "longitude": 80.9462,
        "country": "India",
        "state": "Uttar Pradesh",
        "district": "Lucknow",
        "city": "Lucknow",
        "locality": "Uttar Pradesh",
        "aliases": ["uttar pradesh", "up", "uttarpradesh", "u.p."]
    },
    {
        "name": "West Bengal",
        "formattedAddress": "West Bengal, India",
        "latitude": 22.9868,
        "longitude": 87.8550,
        "country": "India",
        "state": "West Bengal",
        "district": "Kolkata",
        "city": "Kolkata",
        "locality": "West Bengal",
        "aliases": ["west bengal", "wb", "bengal", "w.b.", "paschim banga"]
    },
    {
        "name": "Maharashtra",
        "formattedAddress": "Maharashtra, India",
        "latitude": 19.7515,
        "longitude": 75.7139,
        "country": "India",
        "state": "Maharashtra",
        "district": "Mumbai",
        "city": "Mumbai",
        "locality": "Maharashtra",
        "aliases": ["maharashtra", "mh", "m.h."]
    },
    {
        "name": "Bihar",
        "formattedAddress": "Bihar, India",
        "latitude": 25.0961,
        "longitude": 85.3131,
        "country": "India",
        "state": "Bihar",
        "district": "Patna",
        "city": "Patna",
        "locality": "Bihar",
        "aliases": ["bihar", "br"]
    },
    {
        "name": "Delhi",
        "formattedAddress": "National Capital Territory of Delhi, India",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "country": "India",
        "state": "Delhi",
        "district": "New Delhi",
        "city": "New Delhi",
        "locality": "Delhi",
        "aliases": ["delhi", "new delhi", "ncr", "dilli", "national capital"]
    },
    {
        "name": "Tamil Nadu",
        "formattedAddress": "Tamil Nadu, India",
        "latitude": 11.1271,
        "longitude": 78.6569,
        "country": "India",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "city": "Chennai",
        "locality": "Tamil Nadu",
        "aliases": ["tamil nadu", "tn", "tamilnadu", "tamil nad"]
    },
    {
        "name": "Karnataka",
        "formattedAddress": "Karnataka, India",
        "latitude": 15.3173,
        "longitude": 75.7139,
        "country": "India",
        "state": "Karnataka",
        "district": "Bengaluru",
        "city": "Bengaluru",
        "locality": "Karnataka",
        "aliases": ["karnataka", "ka", "mysore state"]
    },
    {
        "name": "Gujarat",
        "formattedAddress": "Gujarat, India",
        "latitude": 22.2587,
        "longitude": 71.1924,
        "country": "India",
        "state": "Gujarat",
        "district": "Gandhinagar",
        "city": "Gandhinagar",
        "locality": "Gujarat",
        "aliases": ["gujarat", "gj", "gujrat"]
    },
    {
        "name": "Rajasthan",
        "formattedAddress": "Rajasthan, India",
        "latitude": 27.0238,
        "longitude": 74.2179,
        "country": "India",
        "state": "Rajasthan",
        "district": "Jaipur",
        "city": "Jaipur",
        "locality": "Rajasthan",
        "aliases": ["rajasthan", "rj", "rajputana"]
    },
    {
        "name": "Madhya Pradesh",
        "formattedAddress": "Madhya Pradesh, India",
        "latitude": 22.9734,
        "longitude": 78.6569,
        "country": "India",
        "state": "Madhya Pradesh",
        "district": "Bhopal",
        "city": "Bhopal",
        "locality": "Madhya Pradesh",
        "aliases": ["madhya pradesh", "mp", "madhyapradesh", "m.p."]
    },
    {
        "name": "Kerala",
        "formattedAddress": "Kerala, India",
        "latitude": 10.8505,
        "longitude": 76.2711,
        "country": "India",
        "state": "Kerala",
        "district": "Thiruvananthapuram",
        "city": "Thiruvananthapuram",
        "locality": "Kerala",
        "aliases": ["kerala", "kl", "gods own country"]
    },
    {
        "name": "Punjab",
        "formattedAddress": "Punjab, India",
        "latitude": 31.1471,
        "longitude": 75.3412,
        "country": "India",
        "state": "Punjab",
        "district": "Chandigarh",
        "city": "Chandigarh",
        "locality": "Punjab",
        "aliases": ["punjab", "pb"]
    },
    {
        "name": "Haryana",
        "formattedAddress": "Haryana, India",
        "latitude": 29.0588,
        "longitude": 76.0856,
        "country": "India",
        "state": "Haryana",
        "district": "Chandigarh",
        "city": "Chandigarh",
        "locality": "Haryana",
        "aliases": ["haryana", "hr"]
    },
    {
        "name": "Odisha",
        "formattedAddress": "Odisha, India",
        "latitude": 20.9517,
        "longitude": 85.0985,
        "country": "India",
        "state": "Odisha",
        "district": "Bhubaneswar",
        "city": "Bhubaneswar",
        "locality": "Odisha",
        "aliases": ["odisha", "orissa", "od"]
    },
    {
        "name": "Assam",
        "formattedAddress": "Assam, India",
        "latitude": 26.2006,
        "longitude": 92.9376,
        "country": "India",
        "state": "Assam",
        "district": "Dispur",
        "city": "Guwahati",
        "locality": "Assam",
        "aliases": ["assam", "as", "asom"]
    },
    {
        "name": "Telangana",
        "formattedAddress": "Telangana, India",
        "latitude": 18.1124,
        "longitude": 79.0193,
        "country": "India",
        "state": "Telangana",
        "district": "Hyderabad",
        "city": "Hyderabad",
        "locality": "Telangana",
        "aliases": ["telangana", "tg", "ts"]
    },
    {
        "name": "Andhra Pradesh",
        "formattedAddress": "Andhra Pradesh, India",
        "latitude": 15.9129,
        "longitude": 79.7400,
        "country": "India",
        "state": "Andhra Pradesh",
        "district": "Amaravati",
        "city": "Visakhapatnam",
        "locality": "Andhra Pradesh",
        "aliases": ["andhra pradesh", "ap", "andhra"]
    },
    {
        "name": "Chhattisgarh",
        "formattedAddress": "Chhattisgarh, India",
        "latitude": 21.2787,
        "longitude": 81.8661,
        "country": "India",
        "state": "Chhattisgarh",
        "district": "Raipur",
        "city": "Raipur",
        "locality": "Chhattisgarh",
        "aliases": ["chhattisgarh", "cg", "chattisgarh"]
    },
    {
        "name": "Himachal Pradesh",
        "formattedAddress": "Himachal Pradesh, India",
        "latitude": 31.1048,
        "longitude": 77.1734,
        "country": "India",
        "state": "Himachal Pradesh",
        "district": "Shimla",
        "city": "Shimla",
        "locality": "Himachal Pradesh",
        "aliases": ["himachal pradesh", "hp", "himachal"]
    },
    {
        "name": "Uttarakhand",
        "formattedAddress": "Uttarakhand, India",
        "latitude": 30.0668,
        "longitude": 79.0193,
        "country": "India",
        "state": "Uttarakhand",
        "district": "Dehradun",
        "city": "Dehradun",
        "locality": "Uttarakhand",
        "aliases": ["uttarakhand", "uk", "uttaranchal"]
    },
    {
        "name": "Goa",
        "formattedAddress": "Goa, India",
        "latitude": 15.2993,
        "longitude": 74.1240,
        "country": "India",
        "state": "Goa",
        "district": "North Goa",
        "city": "Panaji",
        "locality": "Goa",
        "aliases": ["goa", "ga"]
    },
    {
        "name": "Jammu and Kashmir",
        "formattedAddress": "Jammu and Kashmir, India",
        "latitude": 33.7782,
        "longitude": 76.5762,
        "country": "India",
        "state": "Jammu and Kashmir",
        "district": "Srinagar",
        "city": "Srinagar",
        "locality": "Jammu and Kashmir",
        "aliases": ["jammu and kashmir", "jk", "j&k", "kashmir", "jammu"]
    },
    {
        "name": "Ladakh",
        "formattedAddress": "Ladakh, India",
        "latitude": 34.1526,
        "longitude": 77.5771,
        "country": "India",
        "state": "Ladakh",
        "district": "Leh",
        "city": "Leh",
        "locality": "Ladakh",
        "aliases": ["ladakh", "leh", "kargil"]
    },
    {
        "name": "Tripura",
        "formattedAddress": "Tripura, India",
        "latitude": 23.9408,
        "longitude": 91.9882,
        "country": "India",
        "state": "Tripura",
        "district": "West Tripura",
        "city": "Agartala",
        "locality": "Tripura",
        "aliases": ["tripura", "tr", "agartala"]
    },
    {
        "name": "Meghalaya",
        "formattedAddress": "Meghalaya, India",
        "latitude": 25.4670,
        "longitude": 91.3662,
        "country": "India",
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "city": "Shillong",
        "locality": "Meghalaya",
        "aliases": ["meghalaya", "ml", "shillong"]
    },
    {
        "name": "Manipur",
        "formattedAddress": "Manipur, India",
        "latitude": 24.6637,
        "longitude": 93.9063,
        "country": "India",
        "state": "Manipur",
        "district": "Imphal East",
        "city": "Imphal",
        "locality": "Manipur",
        "aliases": ["manipur", "mn", "imphal"]
    },
    {
        "name": "Nagaland",
        "formattedAddress": "Nagaland, India",
        "latitude": 26.1584,
        "longitude": 94.5624,
        "country": "India",
        "state": "Nagaland",
        "district": "Kohima",
        "city": "Kohima",
        "locality": "Nagaland",
        "aliases": ["nagaland", "nl", "kohima"]
    },
    {
        "name": "Mizoram",
        "formattedAddress": "Mizoram, India",
        "latitude": 23.1645,
        "longitude": 92.9376,
        "country": "India",
        "state": "Mizoram",
        "district": "Aizawl",
        "city": "Aizawl",
        "locality": "Mizoram",
        "aliases": ["mizoram", "mz", "aizawl"]
    },
    {
        "name": "Arunachal Pradesh",
        "formattedAddress": "Arunachal Pradesh, India",
        "latitude": 28.2180,
        "longitude": 94.7278,
        "country": "India",
        "state": "Arunachal Pradesh",
        "district": "Papum Pare",
        "city": "Itanagar",
        "locality": "Arunachal Pradesh",
        "aliases": ["arunachal pradesh", "ar", "itanagar"]
    },
    {
        "name": "Sikkim",
        "formattedAddress": "Sikkim, India",
        "latitude": 27.5330,
        "longitude": 88.5122,
        "country": "India",
        "state": "Sikkim",
        "district": "East Sikkim",
        "city": "Gangtok",
        "locality": "Sikkim",
        "aliases": ["sikkim", "sk", "gangtok"]
    },

    # ----------------------------------------------------
    # 2. Major Indian Cities & District Hubs
    # ----------------------------------------------------
    {
        "name": "Kolkata",
        "formattedAddress": "Kolkata, West Bengal, India",
        "latitude": 22.5726,
        "longitude": 88.3639,
        "country": "India",
        "state": "West Bengal",
        "district": "Kolkata",
        "city": "Kolkata",
        "locality": "Kolkata",
        "aliases": ["kolkata", "calcutta", "kol"]
    },
    {
        "name": "Howrah",
        "formattedAddress": "Howrah, West Bengal, India",
        "latitude": 22.5958,
        "longitude": 88.2636,
        "country": "India",
        "state": "West Bengal",
        "district": "Howrah",
        "city": "Howrah",
        "locality": "Howrah",
        "aliases": ["howrah", "haora"]
    },
    {
        "name": "Ranchi",
        "formattedAddress": "Ranchi, Jharkhand, India",
        "latitude": 23.3441,
        "longitude": 85.3096,
        "country": "India",
        "state": "Jharkhand",
        "district": "Ranchi",
        "city": "Ranchi",
        "locality": "Ranchi",
        "aliases": ["ranchi"]
    },
    {
        "name": "Jamshedpur",
        "formattedAddress": "Jamshedpur, Jharkhand, India",
        "latitude": 22.8046,
        "longitude": 86.2029,
        "country": "India",
        "state": "Jharkhand",
        "district": "East Singhbhum",
        "city": "Jamshedpur",
        "locality": "Jamshedpur",
        "aliases": ["jamshedpur", "tatanagar", "tata"]
    },
    {
        "name": "Dhanbad",
        "formattedAddress": "Dhanbad, Jharkhand, India",
        "latitude": 23.7957,
        "longitude": 86.4304,
        "country": "India",
        "state": "Jharkhand",
        "district": "Dhanbad",
        "city": "Dhanbad",
        "locality": "Dhanbad",
        "aliases": ["dhanbad", "coal capital"]
    },
    {
        "name": "Bokaro Steel City",
        "formattedAddress": "Bokaro, Jharkhand, India",
        "latitude": 23.6693,
        "longitude": 86.1511,
        "country": "India",
        "state": "Jharkhand",
        "district": "Bokaro",
        "city": "Bokaro Steel City",
        "locality": "Bokaro",
        "aliases": ["bokaro", "bokaro steel city", "bs city"]
    },
    {
        "name": "Deoghar",
        "formattedAddress": "Deoghar, Jharkhand, India",
        "latitude": 24.4826,
        "longitude": 86.7001,
        "country": "India",
        "state": "Jharkhand",
        "district": "Deoghar",
        "city": "Deoghar",
        "locality": "Deoghar",
        "aliases": ["deoghar", "baidyanath dham"]
    },
    {
        "name": "Hazaribagh",
        "formattedAddress": "Hazaribagh, Jharkhand, India",
        "latitude": 23.9925,
        "longitude": 85.3637,
        "country": "India",
        "state": "Jharkhand",
        "district": "Hazaribagh",
        "city": "Hazaribagh",
        "locality": "Hazaribagh",
        "aliases": ["hazaribagh", "hazaribag"]
    },
    {
        "name": "Lucknow",
        "formattedAddress": "Lucknow, Uttar Pradesh, India",
        "latitude": 26.8467,
        "longitude": 80.9462,
        "country": "India",
        "state": "Uttar Pradesh",
        "district": "Lucknow",
        "city": "Lucknow",
        "locality": "Lucknow",
        "aliases": ["lucknow", "lko"]
    },
    {
        "name": "Kanpur",
        "formattedAddress": "Kanpur, Uttar Pradesh, India",
        "latitude": 26.4499,
        "longitude": 80.3319,
        "country": "India",
        "state": "Uttar Pradesh",
        "district": "Kanpur Nagar",
        "city": "Kanpur",
        "locality": "Kanpur",
        "aliases": ["kanpur", "cawnpore"]
    },
    {
        "name": "Varanasi",
        "formattedAddress": "Varanasi, Uttar Pradesh, India",
        "latitude": 25.3176,
        "longitude": 82.9739,
        "country": "India",
        "state": "Uttar Pradesh",
        "district": "Varanasi",
        "city": "Varanasi",
        "locality": "Varanasi",
        "aliases": ["varanasi", "banaras", "benares", "kashi"]
    },
    {
        "name": "Prayagraj",
        "formattedAddress": "Prayagraj, Uttar Pradesh, India",
        "latitude": 25.4358,
        "longitude": 81.8463,
        "country": "India",
        "state": "Uttar Pradesh",
        "district": "Prayagraj",
        "city": "Prayagraj",
        "locality": "Prayagraj",
        "aliases": ["prayagraj", "allahabad", "ilhabad"]
    },
    {
        "name": "Agra",
        "formattedAddress": "Agra, Uttar Pradesh, India",
        "latitude": 27.1767,
        "longitude": 78.0081,
        "country": "India",
        "state": "Uttar Pradesh",
        "district": "Agra",
        "city": "Agra",
        "locality": "Agra",
        "aliases": ["agra", "taj city"]
    },
    {
        "name": "Noida",
        "formattedAddress": "Noida, Gautam Buddha Nagar, Uttar Pradesh, India",
        "latitude": 28.5355,
        "longitude": 77.3910,
        "country": "India",
        "state": "Uttar Pradesh",
        "district": "Gautam Buddha Nagar",
        "city": "Noida",
        "locality": "Noida",
        "aliases": ["noida", "greater noida"]
    },
    {
        "name": "Ghaziabad",
        "formattedAddress": "Ghaziabad, Uttar Pradesh, India",
        "latitude": 28.6692,
        "longitude": 77.4538,
        "country": "India",
        "state": "Uttar Pradesh",
        "district": "Ghaziabad",
        "city": "Ghaziabad",
        "locality": "Ghaziabad",
        "aliases": ["ghaziabad"]
    },
    {
        "name": "Mumbai",
        "formattedAddress": "Mumbai, Maharashtra, India",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "country": "India",
        "state": "Maharashtra",
        "district": "Mumbai City",
        "city": "Mumbai",
        "locality": "Mumbai",
        "aliases": ["mumbai", "bombay", "bom"]
    },
    {
        "name": "Pune",
        "formattedAddress": "Pune, Maharashtra, India",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "country": "India",
        "state": "Maharashtra",
        "district": "Pune",
        "city": "Pune",
        "locality": "Pune",
        "aliases": ["pune", "poona"]
    },
    {
        "name": "Nagpur",
        "formattedAddress": "Nagpur, Maharashtra, India",
        "latitude": 21.1458,
        "longitude": 79.0882,
        "country": "India",
        "state": "Maharashtra",
        "district": "Nagpur",
        "city": "Nagpur",
        "locality": "Nagpur",
        "aliases": ["nagpur", "orange city"]
    },
    {
        "name": "Thane",
        "formattedAddress": "Thane, Maharashtra, India",
        "latitude": 19.2183,
        "longitude": 72.9781,
        "country": "India",
        "state": "Maharashtra",
        "district": "Thane",
        "city": "Thane",
        "locality": "Thane",
        "aliases": ["thane"]
    },
    {
        "name": "Nashik",
        "formattedAddress": "Nashik, Maharashtra, India",
        "latitude": 19.9975,
        "longitude": 73.7898,
        "country": "India",
        "state": "Maharashtra",
        "district": "Nashik",
        "city": "Nashik",
        "locality": "Nashik",
        "aliases": ["nashik", "nasik"]
    },
    {
        "name": "Bengaluru",
        "formattedAddress": "Bengaluru, Karnataka, India",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "country": "India",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "city": "Bengaluru",
        "locality": "Bengaluru",
        "aliases": ["bengaluru", "bangalore", "blr"]
    },
    {
        "name": "Mysuru",
        "formattedAddress": "Mysuru, Karnataka, India",
        "latitude": 12.2958,
        "longitude": 76.6394,
        "country": "India",
        "state": "Karnataka",
        "district": "Mysuru",
        "city": "Mysuru",
        "locality": "Mysuru",
        "aliases": ["mysuru", "mysore"]
    },
    {
        "name": "Hyderabad",
        "formattedAddress": "Hyderabad, Telangana, India",
        "latitude": 17.3850,
        "longitude": 78.4867,
        "country": "India",
        "state": "Telangana",
        "district": "Hyderabad",
        "city": "Hyderabad",
        "locality": "Hyderabad",
        "aliases": ["hyderabad", "hyd", "cyberabad"]
    },
    {
        "name": "Chennai",
        "formattedAddress": "Chennai, Tamil Nadu, India",
        "latitude": 13.0827,
        "longitude": 80.2707,
        "country": "India",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "city": "Chennai",
        "locality": "Chennai",
        "aliases": ["chennai", "madras", "maa"]
    },
    {
        "name": "Coimbatore",
        "formattedAddress": "Coimbatore, Tamil Nadu, India",
        "latitude": 11.0168,
        "longitude": 76.9558,
        "country": "India",
        "state": "Tamil Nadu",
        "district": "Coimbatore",
        "city": "Coimbatore",
        "locality": "Coimbatore",
        "aliases": ["coimbatore", "kovai"]
    },
    {
        "name": "Ahmedabad",
        "formattedAddress": "Ahmedabad, Gujarat, India",
        "latitude": 23.0225,
        "longitude": 72.5714,
        "country": "India",
        "state": "Gujarat",
        "district": "Ahmedabad",
        "city": "Ahmedabad",
        "locality": "Ahmedabad",
        "aliases": ["ahmedabad", "amdavad"]
    },
    {
        "name": "Surat",
        "formattedAddress": "Surat, Gujarat, India",
        "latitude": 21.1702,
        "longitude": 72.8311,
        "country": "India",
        "state": "Gujarat",
        "district": "Surat",
        "city": "Surat",
        "locality": "Surat",
        "aliases": ["surat", "diamond city"]
    },
    {
        "name": "Jaipur",
        "formattedAddress": "Jaipur, Rajasthan, India",
        "latitude": 26.9124,
        "longitude": 75.7873,
        "country": "India",
        "state": "Rajasthan",
        "district": "Jaipur",
        "city": "Jaipur",
        "locality": "Jaipur",
        "aliases": ["jaipur", "pink city"]
    },
    {
        "name": "Jodhpur",
        "formattedAddress": "Jodhpur, Rajasthan, India",
        "latitude": 26.2389,
        "longitude": 73.0243,
        "country": "India",
        "state": "Rajasthan",
        "district": "Jodhpur",
        "city": "Jodhpur",
        "locality": "Jodhpur",
        "aliases": ["jodhpur", "blue city"]
    },
    {
        "name": "Patna",
        "formattedAddress": "Patna, Bihar, India",
        "latitude": 25.5941,
        "longitude": 85.1376,
        "country": "India",
        "state": "Bihar",
        "district": "Patna",
        "city": "Patna",
        "locality": "Patna",
        "aliases": ["patna", "patliputra"]
    },
    {
        "name": "Gaya",
        "formattedAddress": "Gaya, Bihar, India",
        "latitude": 24.7914,
        "longitude": 85.0002,
        "country": "India",
        "state": "Bihar",
        "district": "Gaya",
        "city": "Gaya",
        "locality": "Gaya",
        "aliases": ["gaya", "bodhgaya", "bodh gaya"]
    },
    {
        "name": "Bhopal",
        "formattedAddress": "Bhopal, Madhya Pradesh, India",
        "latitude": 23.2599,
        "longitude": 77.4126,
        "country": "India",
        "state": "Madhya Pradesh",
        "district": "Bhopal",
        "city": "Bhopal",
        "locality": "Bhopal",
        "aliases": ["bhopal", "city of lakes"]
    },
    {
        "name": "Indore",
        "formattedAddress": "Indore, Madhya Pradesh, India",
        "latitude": 22.7196,
        "longitude": 75.8577,
        "country": "India",
        "state": "Madhya Pradesh",
        "district": "Indore",
        "city": "Indore",
        "locality": "Indore",
        "aliases": ["indore"]
    },
    {
        "name": "Gwalior",
        "formattedAddress": "Gwalior, Madhya Pradesh, India",
        "latitude": 26.2183,
        "longitude": 78.1828,
        "country": "India",
        "state": "Madhya Pradesh",
        "district": "Gwalior",
        "city": "Gwalior",
        "locality": "Gwalior",
        "aliases": ["gwalior"]
    },
    {
        "name": "Gurugram",
        "formattedAddress": "Gurugram, Haryana, India",
        "latitude": 28.4595,
        "longitude": 77.0266,
        "country": "India",
        "state": "Haryana",
        "district": "Gurugram",
        "city": "Gurugram",
        "locality": "Gurugram",
        "aliases": ["gurugram", "gurgaon", "cyber city"]
    },
    {
        "name": "Chandigarh",
        "formattedAddress": "Chandigarh, India",
        "latitude": 30.7333,
        "longitude": 76.7794,
        "country": "India",
        "state": "Chandigarh",
        "district": "Chandigarh",
        "city": "Chandigarh",
        "locality": "Chandigarh",
        "aliases": ["chandigarh", "chd"]
    },
    {
        "name": "Amritsar",
        "formattedAddress": "Amritsar, Punjab, India",
        "latitude": 31.6340,
        "longitude": 74.8723,
        "country": "India",
        "state": "Punjab",
        "district": "Amritsar",
        "city": "Amritsar",
        "locality": "Amritsar",
        "aliases": ["amritsar", "golden temple city"]
    },
    {
        "name": "Ludhiana",
        "formattedAddress": "Ludhiana, Punjab, India",
        "latitude": 30.9010,
        "longitude": 75.8573,
        "country": "India",
        "state": "Punjab",
        "district": "Ludhiana",
        "city": "Ludhiana",
        "locality": "Ludhiana",
        "aliases": ["ludhiana"]
    },
    {
        "name": "Bhubaneswar",
        "formattedAddress": "Bhubaneswar, Odisha, India",
        "latitude": 20.2961,
        "longitude": 85.8245,
        "country": "India",
        "state": "Odisha",
        "district": "Khordha",
        "city": "Bhubaneswar",
        "locality": "Bhubaneswar",
        "aliases": ["bhubaneswar", "bhubaneshwar", "bbsr"]
    },
    {
        "name": "Cuttack",
        "formattedAddress": "Cuttack, Odisha, India",
        "latitude": 20.4625,
        "longitude": 85.8830,
        "country": "India",
        "state": "Odisha",
        "district": "Cuttack",
        "city": "Cuttack",
        "locality": "Cuttack",
        "aliases": ["cuttack", "silver city"]
    },
    {
        "name": "Guwahati",
        "formattedAddress": "Guwahati, Assam, India",
        "latitude": 26.1445,
        "longitude": 91.7362,
        "country": "India",
        "state": "Assam",
        "district": "Kamrup Metropolitan",
        "city": "Guwahati",
        "locality": "Guwahati",
        "aliases": ["guwahati", "gauhati", "ghy"]
    },
    {
        "name": "Visakhapatnam",
        "formattedAddress": "Visakhapatnam, Andhra Pradesh, India",
        "latitude": 17.6868,
        "longitude": 83.2185,
        "country": "India",
        "state": "Andhra Pradesh",
        "district": "Visakhapatnam",
        "city": "Visakhapatnam",
        "locality": "Visakhapatnam",
        "aliases": ["visakhapatnam", "vizag", "waltair"]
    },
    {
        "name": "Kochi",
        "formattedAddress": "Kochi, Kerala, India",
        "latitude": 9.9312,
        "longitude": 76.2673,
        "country": "India",
        "state": "Kerala",
        "district": "Ernakulam",
        "city": "Kochi",
        "locality": "Kochi",
        "aliases": ["kochi", "cochin", "ernakulam"]
    },
    {
        "name": "Thiruvananthapuram",
        "formattedAddress": "Thiruvananthapuram, Kerala, India",
        "latitude": 8.5241,
        "longitude": 76.9366,
        "country": "India",
        "state": "Kerala",
        "district": "Thiruvananthapuram",
        "city": "Thiruvananthapuram",
        "locality": "Thiruvananthapuram",
        "aliases": ["thiruvananthapuram", "trivandrum", "tvm"]
    },
    {
        "name": "Srinagar",
        "formattedAddress": "Srinagar, Jammu and Kashmir, India",
        "latitude": 34.0837,
        "longitude": 74.7973,
        "country": "India",
        "state": "Jammu and Kashmir",
        "district": "Srinagar",
        "city": "Srinagar",
        "locality": "Srinagar",
        "aliases": ["srinagar"]
    },
    {
        "name": "Jammu",
        "formattedAddress": "Jammu, Jammu and Kashmir, India",
        "latitude": 32.7266,
        "longitude": 74.8570,
        "country": "India",
        "state": "Jammu and Kashmir",
        "district": "Jammu",
        "city": "Jammu",
        "locality": "Jammu",
        "aliases": ["jammu", "city of temples"]
    },
    {
        "name": "Shimla",
        "formattedAddress": "Shimla, Himachal Pradesh, India",
        "latitude": 31.1048,
        "longitude": 77.1734,
        "country": "India",
        "state": "Himachal Pradesh",
        "district": "Shimla",
        "city": "Shimla",
        "locality": "Shimla",
        "aliases": ["shimla", "simla"]
    },
    {
        "name": "Dehradun",
        "formattedAddress": "Dehradun, Uttarakhand, India",
        "latitude": 30.3165,
        "longitude": 78.0322,
        "country": "India",
        "state": "Uttarakhand",
        "district": "Dehradun",
        "city": "Dehradun",
        "locality": "Dehradun",
        "aliases": ["dehradun", "doon"]
    },
    {
        "name": "Durgapur",
        "formattedAddress": "Durgapur, Paschim Bardhaman, West Bengal, India",
        "latitude": 23.5204,
        "longitude": 87.3119,
        "country": "India",
        "state": "West Bengal",
        "district": "Paschim Bardhaman",
        "city": "Durgapur",
        "locality": "Durgapur",
        "aliases": ["durgapur", "steel city of bengal"]
    },
    {
        "name": "Asansol",
        "formattedAddress": "Asansol, Paschim Bardhaman, West Bengal, India",
        "latitude": 23.6739,
        "longitude": 86.9524,
        "country": "India",
        "state": "West Bengal",
        "district": "Paschim Bardhaman",
        "city": "Asansol",
        "locality": "Asansol",
        "aliases": ["asansol"]
    },
    {
        "name": "Siliguri",
        "formattedAddress": "Siliguri, Darjeeling, West Bengal, India",
        "latitude": 26.7271,
        "longitude": 88.3953,
        "country": "India",
        "state": "West Bengal",
        "district": "Darjeeling",
        "city": "Siliguri",
        "locality": "Siliguri",
        "aliases": ["siliguri"]
    },
    {
        "name": "Darjeeling",
        "formattedAddress": "Darjeeling, West Bengal, India",
        "latitude": 27.0410,
        "longitude": 88.2663,
        "country": "India",
        "state": "West Bengal",
        "district": "Darjeeling",
        "city": "Darjeeling",
        "locality": "Darjeeling",
        "aliases": ["darjeeling", "queen of the hills"]
    },
    {
        "name": "Kharagpur",
        "formattedAddress": "Kharagpur, Paschim Medinipur, West Bengal, India",
        "latitude": 22.3392,
        "longitude": 87.3253,
        "country": "India",
        "state": "West Bengal",
        "district": "Paschim Medinipur",
        "city": "Kharagpur",
        "locality": "Kharagpur",
        "aliases": ["kharagpur", "kharagpore", "kgp"]
    },

    # ----------------------------------------------------
    # 3. Major Global Countries, Capitals & Mega-Cities
    # ----------------------------------------------------
    {
        "name": "Seoul",
        "formattedAddress": "Seoul, South Korea",
        "latitude": 37.5665,
        "longitude": 126.9780,
        "country": "South Korea",
        "state": "Seoul Special City",
        "district": "Jung-gu",
        "city": "Seoul",
        "locality": "Seoul",
        "aliases": ["seoul", "south korea", "korea south", "republic of korea", "kr"]
    },
    {
        "name": "Pyongyang",
        "formattedAddress": "Pyongyang, North Korea",
        "latitude": 39.0392,
        "longitude": 125.7625,
        "country": "North Korea",
        "state": "Pyongyang",
        "district": "Chung-guyok",
        "city": "Pyongyang",
        "locality": "Pyongyang",
        "aliases": ["pyongyang", "north korea", "korea north", "dprk"]
    },
    {
        "name": "Tokyo",
        "formattedAddress": "Tokyo, Japan",
        "latitude": 35.6762,
        "longitude": 139.6503,
        "country": "Japan",
        "state": "Tokyo Metropolis",
        "district": "Shinjuku",
        "city": "Tokyo",
        "locality": "Tokyo",
        "aliases": ["tokyo", "japan", "jp"]
    },
    {
        "name": "Osaka",
        "formattedAddress": "Osaka, Japan",
        "latitude": 34.6937,
        "longitude": 135.5023,
        "country": "Japan",
        "state": "Osaka Prefecture",
        "district": "Chuo-ku",
        "city": "Osaka",
        "locality": "Osaka",
        "aliases": ["osaka"]
    },
    {
        "name": "London",
        "formattedAddress": "London, Greater London, United Kingdom",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "country": "United Kingdom",
        "state": "Greater London",
        "district": "City of Westminster",
        "city": "London",
        "locality": "London",
        "aliases": ["london", "uk", "united kingdom", "great britain", "england"]
    },
    {
        "name": "Manchester",
        "formattedAddress": "Manchester, Greater Manchester, United Kingdom",
        "latitude": 53.4808,
        "longitude": -2.2426,
        "country": "United Kingdom",
        "state": "Greater Manchester",
        "district": "Manchester",
        "city": "Manchester",
        "locality": "Manchester",
        "aliases": ["manchester"]
    },
    {
        "name": "New York",
        "formattedAddress": "New York, NY, United States",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "country": "United States",
        "state": "New York",
        "district": "New York County",
        "city": "New York",
        "locality": "New York",
        "aliases": ["new york", "nyc", "new york city", "usa", "manhattan"]
    },
    {
        "name": "Washington, D.C.",
        "formattedAddress": "Washington, District of Columbia, United States",
        "latitude": 38.9072,
        "longitude": -77.0369,
        "country": "United States",
        "state": "District of Columbia",
        "district": "District of Columbia",
        "city": "Washington",
        "locality": "Washington",
        "aliases": ["washington", "washington dc", "dc", "d.c."]
    },
    {
        "name": "Los Angeles",
        "formattedAddress": "Los Angeles, CA, United States",
        "latitude": 34.0522,
        "longitude": -118.2437,
        "country": "United States",
        "state": "California",
        "district": "Los Angeles County",
        "city": "Los Angeles",
        "locality": "Los Angeles",
        "aliases": ["los angeles", "la", "california"]
    },
    {
        "name": "San Francisco",
        "formattedAddress": "San Francisco, CA, United States",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "country": "United States",
        "state": "California",
        "district": "San Francisco County",
        "city": "San Francisco",
        "locality": "San Francisco",
        "aliases": ["san francisco", "sf", "bay area", "silicon valley"]
    },
    {
        "name": "Paris",
        "formattedAddress": "Paris, Île-de-France, France",
        "latitude": 48.8566,
        "longitude": 2.3522,
        "country": "France",
        "state": "Île-de-France",
        "district": "Paris",
        "city": "Paris",
        "locality": "Paris",
        "aliases": ["paris", "france", "fr"]
    },
    {
        "name": "Berlin",
        "formattedAddress": "Berlin, Germany",
        "latitude": 52.5200,
        "longitude": 13.4050,
        "country": "Germany",
        "state": "Berlin",
        "district": "Mitte",
        "city": "Berlin",
        "locality": "Berlin",
        "aliases": ["berlin", "germany", "deutschland", "de"]
    },
    {
        "name": "Rome",
        "formattedAddress": "Rome, Lazio, Italy",
        "latitude": 41.9028,
        "longitude": 12.4964,
        "country": "Italy",
        "state": "Lazio",
        "district": "Metropolitan City of Rome Capital",
        "city": "Rome",
        "locality": "Rome",
        "aliases": ["rome", "roma", "italy", "italia", "it"]
    },
    {
        "name": "Madrid",
        "formattedAddress": "Madrid, Community of Madrid, Spain",
        "latitude": 40.4168,
        "longitude": -3.7038,
        "country": "Spain",
        "state": "Community of Madrid",
        "district": "Madrid",
        "city": "Madrid",
        "locality": "Madrid",
        "aliases": ["madrid", "spain", "españa", "es"]
    },
    {
        "name": "Dubai",
        "formattedAddress": "Dubai, United Arab Emirates",
        "latitude": 25.2048,
        "longitude": 55.2708,
        "country": "United Arab Emirates",
        "state": "Emirate of Dubai",
        "district": "Dubai",
        "city": "Dubai",
        "locality": "Dubai",
        "aliases": ["dubai", "uae", "united arab emirates"]
    },
    {
        "name": "Abu Dhabi",
        "formattedAddress": "Abu Dhabi, United Arab Emirates",
        "latitude": 24.4539,
        "longitude": 54.3773,
        "country": "United Arab Emirates",
        "state": "Emirate of Abu Dhabi",
        "district": "Abu Dhabi",
        "city": "Abu Dhabi",
        "locality": "Abu Dhabi",
        "aliases": ["abu dhabi"]
    },
    {
        "name": "Singapore",
        "formattedAddress": "Singapore",
        "latitude": 1.3521,
        "longitude": 103.8198,
        "country": "Singapore",
        "state": "Central Region",
        "district": "Singapore",
        "city": "Singapore",
        "locality": "Singapore",
        "aliases": ["singapore", "sg"]
    },
    {
        "name": "Bangkok",
        "formattedAddress": "Bangkok, Thailand",
        "latitude": 13.7563,
        "longitude": 100.5018,
        "country": "Thailand",
        "state": "Bangkok",
        "district": "Phra Nakhon",
        "city": "Bangkok",
        "locality": "Bangkok",
        "aliases": ["bangkok", "thailand", "krung thep"]
    },
    {
        "name": "Kuala Lumpur",
        "formattedAddress": "Kuala Lumpur, Malaysia",
        "latitude": 3.1390,
        "longitude": 101.6869,
        "country": "Malaysia",
        "state": "Federal Territory of Kuala Lumpur",
        "district": "Kuala Lumpur",
        "city": "Kuala Lumpur",
        "locality": "Kuala Lumpur",
        "aliases": ["kuala lumpur", "kl", "malaysia"]
    },
    {
        "name": "Jakarta",
        "formattedAddress": "Jakarta, Indonesia",
        "latitude": -6.2088,
        "longitude": 106.8456,
        "country": "Indonesia",
        "state": "Special Capital Region of Jakarta",
        "district": "Central Jakarta",
        "city": "Jakarta",
        "locality": "Jakarta",
        "aliases": ["jakarta", "indonesia"]
    },
    {
        "name": "Sydney",
        "formattedAddress": "Sydney, New South Wales, Australia",
        "latitude": -33.8688,
        "longitude": 151.2093,
        "country": "Australia",
        "state": "New South Wales",
        "district": "City of Sydney",
        "city": "Sydney",
        "locality": "Sydney",
        "aliases": ["sydney", "australia", "nsw"]
    },
    {
        "name": "Melbourne",
        "formattedAddress": "Melbourne, Victoria, Australia",
        "latitude": -37.8136,
        "longitude": 144.9631,
        "country": "Australia",
        "state": "Victoria",
        "district": "City of Melbourne",
        "city": "Melbourne",
        "locality": "Melbourne",
        "aliases": ["melbourne", "vic"]
    },
    {
        "name": "Toronto",
        "formattedAddress": "Toronto, Ontario, Canada",
        "latitude": 43.6532,
        "longitude": -79.3832,
        "country": "Canada",
        "state": "Ontario",
        "district": "Toronto",
        "city": "Toronto",
        "locality": "Toronto",
        "aliases": ["toronto", "canada", "on"]
    },
    {
        "name": "Beijing",
        "formattedAddress": "Beijing, China",
        "latitude": 39.9042,
        "longitude": 116.4074,
        "country": "China",
        "state": "Beijing Municipality",
        "district": "Dongcheng",
        "city": "Beijing",
        "locality": "Beijing",
        "aliases": ["beijing", "peking", "china", "cn"]
    },
    {
        "name": "Shanghai",
        "formattedAddress": "Shanghai, China",
        "latitude": 31.2304,
        "longitude": 121.4737,
        "country": "China",
        "state": "Shanghai Municipality",
        "district": "Huangpu",
        "city": "Shanghai",
        "locality": "Shanghai",
        "aliases": ["shanghai"]
    },
    {
        "name": "Moscow",
        "formattedAddress": "Moscow, Russia",
        "latitude": 55.7558,
        "longitude": 37.6173,
        "country": "Russia",
        "state": "Federal City of Moscow",
        "district": "Central Administrative Okrug",
        "city": "Moscow",
        "locality": "Moscow",
        "aliases": ["moscow", "russia", "ru"]
    },
    {
        "name": "Cairo",
        "formattedAddress": "Cairo, Egypt",
        "latitude": 30.0444,
        "longitude": 31.2357,
        "country": "Egypt",
        "state": "Cairo Governorate",
        "district": "Cairo",
        "city": "Cairo",
        "locality": "Cairo",
        "aliases": ["cairo", "egypt"]
    },
    {
        "name": "Johannesburg",
        "formattedAddress": "Johannesburg, Gauteng, South Africa",
        "latitude": -26.2041,
        "longitude": 28.0473,
        "country": "South Africa",
        "state": "Gauteng",
        "district": "City of Johannesburg",
        "city": "Johannesburg",
        "locality": "Johannesburg",
        "aliases": ["johannesburg", "south africa", "joburg"]
    },
    {
        "name": "Dhaka",
        "formattedAddress": "Dhaka, Bangladesh",
        "latitude": 23.8103,
        "longitude": 90.4125,
        "country": "Bangladesh",
        "state": "Dhaka Division",
        "district": "Dhaka District",
        "city": "Dhaka",
        "locality": "Dhaka",
        "aliases": ["dhaka", "bangladesh", "dacca"]
    },
    {
        "name": "Colombo",
        "formattedAddress": "Colombo, Western Province, Sri Lanka",
        "latitude": 6.9271,
        "longitude": 79.8612,
        "country": "Sri Lanka",
        "state": "Western Province",
        "district": "Colombo District",
        "city": "Colombo",
        "locality": "Colombo",
        "aliases": ["colombo", "sri lanka"]
    },
    {
        "name": "Kathmandu",
        "formattedAddress": "Kathmandu, Bagmati Province, Nepal",
        "latitude": 27.7172,
        "longitude": 85.3240,
        "country": "Nepal",
        "state": "Bagmati Province",
        "district": "Kathmandu District",
        "city": "Kathmandu",
        "locality": "Kathmandu",
        "aliases": ["kathmandu", "nepal"]
    },
    {
        "name": "Islamabad",
        "formattedAddress": "Islamabad, Islamabad Capital Territory, Pakistan",
        "latitude": 33.6844,
        "longitude": 73.0479,
        "country": "Pakistan",
        "state": "Islamabad Capital Territory",
        "district": "Islamabad",
        "city": "Islamabad",
        "locality": "Islamabad",
        "aliases": ["islamabad", "pakistan"]
    },
    {
        "name": "Zurich",
        "formattedAddress": "Zurich, Switzerland",
        "latitude": 47.3769,
        "longitude": 8.5417,
        "country": "Switzerland",
        "state": "Canton of Zurich",
        "district": "Zurich",
        "city": "Zurich",
        "locality": "Zurich",
        "aliases": ["zurich", "zürich", "switzerland"]
    },
    {
        "name": "Amsterdam",
        "formattedAddress": "Amsterdam, North Holland, Netherlands",
        "latitude": 52.3676,
        "longitude": 4.9041,
        "country": "Netherlands",
        "state": "North Holland",
        "district": "Amsterdam",
        "city": "Amsterdam",
        "locality": "Amsterdam",
        "aliases": ["amsterdam", "netherlands", "holland"]
    }
]

def search_preindexed_locations(query: str, limit: int = 6) -> List[LocationSearchItem]:
    """
    Blazingly fast (<1ms) in-memory substring & alias search against pre-indexed
    Indian States, major cities/districts, and global capitals.
    Ranks exact/prefix matches highest.
    """
    clean = query.strip().lower()
    if not clean or len(clean) < 2:
        return []

    exact_matches: List[Dict[str, Any]] = []
    prefix_matches: List[Dict[str, Any]] = []
    alias_matches: List[Dict[str, Any]] = []
    substring_matches: List[Dict[str, Any]] = []

    for item in _GEO_DATA:
        name_lower = item["name"].lower()
        state_lower = item["state"].lower()
        country_lower = item["country"].lower()
        city_lower = item["city"].lower()
        aliases = [a.lower() for a in item.get("aliases", [])]

        if name_lower == clean or any(a == clean for a in aliases):
            exact_matches.append(item)
        elif name_lower.startswith(clean) or any(a.startswith(clean) for a in aliases):
            prefix_matches.append(item)
        elif clean in aliases:
            alias_matches.append(item)
        elif clean in name_lower or clean in state_lower or clean in city_lower or clean in country_lower or any(clean in a for a in aliases):
            substring_matches.append(item)

    combined: List[Dict[str, Any]] = []
    seen_ids = set()

    for candidate_list in (exact_matches, prefix_matches, alias_matches, substring_matches):
        for item in candidate_list:
            cid = f"{item['latitude']}_{item['longitude']}"
            if cid not in seen_ids:
                seen_ids.add(cid)
                combined.append(item)
                if len(combined) >= limit:
                    break
        if len(combined) >= limit:
            break

    results: List[LocationSearchItem] = []
    for it in combined:
        results.append(LocationSearchItem(
            id=abs(hash(f"{it['name']}_{it['latitude']}_{it['longitude']}")) % 1000000,
            name=it["name"],
            formattedAddress=it["formattedAddress"],
            latitude=it["latitude"],
            longitude=it["longitude"],
            country=it["country"],
            state=it["state"],
            district=it.get("district", ""),
            city=it.get("city", it["name"]),
            locality=it.get("locality", it["name"]),
            sublocality="",
            neighborhood="",
            postalCode="",
            placeId=f"geo_{abs(hash(it['name'])) % 1000000}",
            admin1=it["state"],
            admin2=it.get("district", "")
        ))

    return results
