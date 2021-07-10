import asyncio
import cv2
import numpy as np
from scipy import rand
import websockets
import base64
import json
import os
import torch
import time
import operator
import random
  


model = torch.hub.load('ultralytics/yolov5', 'custom', path='./best.pt') 
model.conf = 0.45  # confidence threshold (0-1)
model.iou = 0.9  # NMS IoU threshold (0-1)


def distance(point_1, point_2):
    return 0


def catch_corona(wave_image, threshold=0.8):
 
    result = model(wave_image, size = 800)

    # p = random.random()

    # if (p > 0.5):
    #     result.show()

    np_rs = result.xywh[0].cpu()

    # print(np_rs)

    doctor = [(np.float16(r[0]) , np.float16(r[1])) for r in np_rs if r[5] == 0]
    rs = [(np.float16(r[0]) , np.float16(r[1])) for r in np_rs if r[5] != 0 and r[5] != 2]

    rs_ = []
    for virus in rs:
        valid = True
        for doc in doctor:
            if sum([abs(x) for x in map(operator.sub, doc, virus)]) < 200:
                valid = False
                break
            if valid:
                rs_.append(virus) 

    if (len(rs_)) == 0:
        return [(0,0)]
    


    return rs_

def base64_to_image(base64_data):
    encoded_data = base64_data.split(',')[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)[:, :, ::-1]

    return img

async def play_game(websocket, path):
    print('Corona Killer is ready to play!')
    catchings = []
    last_round_id = ''
    wave_count = 0
    

    # t = time.time()

    while True:
        ### receive a socket message (wave)
        try:
            data = await websocket.recv()

        except Exception as e:
            print('Error: ' + e)
            break

        json_data = json.loads(data)

        # print(json_data)

        ### check if starting a new round
        if json_data["roundId"] != last_round_id:
            print(f'> Catching corona for round {json_data["roundId"]}...')
            last_round_id = json_data["roundId"]

        ### catch corona in a wave image
        wave_image = base64_to_image(json_data['base64Image'])
        results = catch_corona(wave_image)


        
        # waves_dir = f'waves/{last_round_id}/'
        # if not os.path.exists(waves_dir):
        #     os.makedirs(waves_dir)
            
        # cv2.imwrite(os.path.join(waves_dir, f'{json_data["waveId"]}.jpg'), wave_image)

        print(f'>>> Wave #{wave_count:03d}: {json_data["waveId"]}')
        wave_count = wave_count + 1

        ### store catching positions in the list

        positions = [
            {
                "x" : float(rs[0]),
                "y" : float(rs[1])
            }
            for rs in results
        ]

        # print(positions)


        catchings.append({
            "positions": positions,
            "waveId": json_data["waveId"]  
        })

        # print(catchings)

        ### send result to websocket if it is the last wave
        if json_data["isLastWave"]:
            round_id = json_data["roundId"]
            print(f'> Submitting result for round {round_id}...')

            json_result = {
                "roundId": round_id,
                "catchings": catchings,
            }

            with open('rs.json', 'w') as f:
                json.dump(json_result, f)

            await websocket.send(json.dumps(json_result))
            print('> Submitted.')
           

            catchings = []
            wave_count = 0
            # print((time.time() - t))


start_server = websockets.serve(play_game, "localhost", 8769, max_size=100000000)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
