import shazamio
import asyncio

class Shazam:
    def __init__(self):
        self.shazam = shazamio.Shazam()

    async def recognize_async(self, filename):
        return await self.shazam.recognize(filename)

    def recognize(self, filename):
        return asyncio.run(self.recognize_async(filename))


