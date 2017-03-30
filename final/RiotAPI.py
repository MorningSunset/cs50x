import requests
import RiotConsts as Consts
API_KEY = "RGAPI-81e7f2b8-4e9e-4385-9239-2763f7db5fda"
summoner = "NoctiousIMG"
URL = "https://na.api.pvp.net/api/lol/na/v1.4/summoner/by-name/{name}"

class RiotAPI(object):
    def __init__(self, api_key, region="na"):
        self.api_key = api_key
        self.region = region
        
    def _request(self, api_url, params={}):
        args = {'api_key': self.api_key }
        for key, value in params.items():
            if key not in args:
                args[key] = value
        response = requests.get(
            Consts.URL['base'].format(
                url=api_url
                ),
            params=args
            )
        return response.json()
    
    def get_summoner_by_name(self, names):
        api_url = Consts.URL['summoner by name'].format(
            name=names
            )
        return self._request(api_url)
        
    def get_league(self, sum_id):
        api_url = Consts.URL['league by name'].format(
            id=sum_id
            )
        return self._request(api_url)
        
    def get_history(self, sum_id):
        api_url = Consts.URL['match by id'].format(
            id=sum_id
            )
        return self._request(api_url)
    
    def get_matches(self, sum_id):
        api_url = Consts.URL['recent by id'].format(
            id=sum_id
            )
        return self._request(api_url)