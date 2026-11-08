import asyncio
import sys
from opentele.td.account import MapData, lskType, QByteArray, td, TDataReadMapDataFailed, UseCurrentSession
from opentele.td.tdesktop import TDesktop
from telethon import events

def patched_read(self, localKey, legacyPasscode=QByteArray()):
    mapData = td.Storage.ReadFile('map', self.basePath)
    legacySalt, legacyKeyEncrypted, mapEncrypted = QByteArray(), QByteArray(), QByteArray()
    mapData.stream >> legacySalt >> legacyKeyEncrypted >> mapEncrypted
    map_stream = td.Storage.DecryptLocal(mapEncrypted, localKey)
    while not map_stream.stream.atEnd():
        keyType = map_stream.stream.readUInt32()
        if keyType == lskType.lskSelfSerialized:
            selfSerialized = QByteArray()
            map_stream.stream >> selfSerialized
            self._selfSerialized = selfSerialized
        elif keyType in (lskType.lskLocations, lskType.lskTrustedBots, lskType.lskUserSettings, lskType.lskRecentHashtagsAndBots, lskType.lskExportSettings, lskType.lskFavedStickers, lskType.lskSavedGifs):
            map_stream.stream.readUInt64()
        elif keyType in (lskType.lskBackgroundOld,):
            map_stream.stream.readUInt64()
            map_stream.stream.readUInt64()
        elif keyType in (lskType.lskStickersKeys, lskType.lskMasksKeys):
            for _ in range(4): map_stream.stream.readUInt64()
        elif keyType in (lskType.lskDraft, lskType.lskDraftPosition):
            cnt = map_stream.stream.readUInt32()
            for _ in range(cnt):
                map_stream.stream.readUInt64()
                map_stream.stream.readUInt64()
        else:
            try: map_stream.stream.readUInt64()
            except Exception: pass
    self._oldMapVersion = mapData.version

MapData.read = patched_read

tdata = r'c:\Users\user\Desktop\Pomoshgram_PC\tdata'
td_obj = TDesktop(tdata)

async def test():
    client = await td_obj.mainAccount.ToTelethon(flag=UseCurrentSession)
    await client.connect()

    print("Listening to ALL events for 15 seconds. Please send ANY message in Telegram Desktop now!")
    
    @client.on(events.Raw)
    async def raw_h(event):
        print(f"[RAW] {type(event).__name__}")

    @client.on(events.NewMessage)
    async def nm_h(event):
        print(f"[NewMessage] out={event.out} text={event.text} chat_id={event.chat_id} sender_id={event.sender_id}")

    try:
        await asyncio.wait_for(client.run_until_disconnected(), timeout=12)
    except asyncio.TimeoutError:
        print("Timeout reached, finished listening.")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test())
