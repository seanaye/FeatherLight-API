from asyncio import iscoroutinefunction

class Base_User:

    def __init__(self, userid):
        self.userid = userid


    async def execute(self, api_method):
        if iscoroutinefunction(api_method.run):
            return await api_method.run(self)
        return api_method.run(self)