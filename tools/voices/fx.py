# the ffmpeg effects each voice gets (shared by pack.py and add_new.py)
TRIM = "silenceremove=start_periods=1:start_threshold=-48dB,areverse,silenceremove=start_periods=1:start_threshold=-48dB,areverse"
FX = {
  # Madman: a big rough bloke: pitched down (formants too, so he sounds bigger), chest and low-mid weight, the nasal band
  # cut, some bite up top, driven hard into soft clipping with a fast flutter for gravel
  'mm': TRIM + ",asetrate=24000*0.86,aresample=24000,atempo=1.12,equalizer=f=140:t=q:w=0.9:g=5,equalizer=f=420:t=q:w=1:g=2,equalizer=f=1500:t=q:w=1.2:g=-4,equalizer=f=3200:t=q:w=1.4:g=2,tremolo=f=28:d=0.18,volume=4.5,asoftclip=type=tanh,lowpass=f=6200",
  # the backpackers off one French voice: Chloe as recorded, the two blokes pitched down (formants and all, so they sound bigger)
  # Dima: a huge Russian: pitched down a little, a big chest and a slow, heavy delivery, clean (no gravel; he's healthy)
  'dm': TRIM + ",asetrate=24000*0.9,aresample=24000,atempo=1.04,equalizer=f=110:t=q:w=0.9:g=6,equalizer=f=300:t=q:w=1:g=2,equalizer=f=2600:t=q:w=1.2:g=1.5,acompressor=threshold=0.12:ratio=3:attack=5:release=80,volume=2",
  # Matt: his own recordings (Voicebox, off his voice profile), just trimmed and levelled
  'mt': TRIM,
  'C': TRIM, 'M': TRIM + ",asetrate=24000*0.82,aresample=24000,atempo=1.2195", 'A': TRIM + ",asetrate=24000*0.77,aresample=24000,atempo=1.2987",
}
