import pygame
import boto3
import json
import base64
import io

#init
pygame.init()
pygame.mixer.quit()
pygame.mouse.set_visible(0)
size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
screen = pygame.display.set_mode(size, pygame.FULLSCREEN)

canvas = pygame.Rect(40, 0, 480, 480)
clear = pygame.Rect(530,480-150-10,50,150)
submit = pygame.Rect(530,480-150-310,50,150)
new_prompt = pygame.Rect(0, 0, 40, 40)

bedrock = boto3.client(service_name='bedrock-runtime')
accept = "application/json"
content_type = "application/json"
screen_state = ""


def get_prompt():
    body = json.dumps({
            "inputText": "Generate a drawing prompt in the format \"Draw a {animal or occupation} {verb}ing a {noun}\".  Only return the prompt, and fill in all the blanks. The sentence shouldn't make sense.",
            "textGenerationConfig": {
                "maxTokenCount": 4096,
                "stopSequences": [],
                "temperature": 1,
                "topP": 1
            }
        })
    response = bedrock.invoke_model(
        body=body, modelId="amazon.titan-text-lite-v1", accept=accept, contentType=content_type
    )
    response_body = json.loads(response.get("body").read())
    return response_body['results'][0]['outputText'].strip()

prompt = get_prompt()

# draw area
def setup_draw():
    screen.fill((0,0,0))
    s = pygame.transform.rotate(screen, -90)
    #prompt
    font = pygame.font.Font('segoeui.ttf', 24)
    s.blit(font.render(prompt, True, (255,255,255)), (0, 0))
    #new prompt
    reload_img = pygame.image.load("clockwise-rotation.png")
    s.blit(reload_img, (442,2))
    #pygame.draw.rect(s, (255,255,255), (440,0,40,40), 3)
    #canvas area
    pygame.draw.rect(s, (255, 255, 255), (0, 40, 480, 480), 3)
    #clear
    pygame.draw.rect(s, (255,255,255), (10, 530, 150, 50), 3)
    s.blit(font.render("Clear", True, (255,255,255)), (58, 537))
    #submit
    pygame.draw.rect(s, (255, 255, 255), (310, 530, 150, 50), 3)
    s.blit(font.render("Submit", True, (255, 255,255)), (350, 537))
    #draw to screen
    screen.blit(pygame.transform.rotate(s, 90), (0,0))
    pygame.display.update()
    scren_state = "draw"

setup_draw()

def submit_pic():
    #get image from screen
    s = pygame.transform.rotate(screen, -90)
    simg = s.subsurface(0, 40, 480, 480)
    data = io.BytesIO()
    pygame.image.save(simg, data, 'PNG')
    b64data = base64.b64encode(data.getvalue())
    body = json.dumps({
            "taskType": "IMAGE_VARIATION",
            "imageVariationParams": {
                "text": prompt,
                "images": [b64data.decode('utf-8')]
            },
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "width": 512,
                "height": 512,
                "cfgScale": 8.0
            }
        })
    response = bedrock.invoke_model(
        body=body, modelId='amazon.titan-image-generator-v1', accept=accept, contentType=content_type
    )
    response_body = json.loads(response.get("body").read())

    base64_image = response_body.get("images")[0]
    base64_bytes = base64_image.encode('ascii')
    image_bytes = base64.b64decode(base64_bytes)
    output = io.BytesIO(image_bytes)
    newimg = pygame.image.load(output).convert()
    draw_result(newimg)

def draw_result(newimg):    
    s = pygame.transform.rotate(screen, -90)
    scale = 1 + ((480 - 512) / 512)
    imgscale = pygame.transform.scale(newimg, (int(512 * scale), int(512 * scale)))
    #imgscale = pygame.transform.flip(imgscale, 1, 0)
    s.fill((0,0,0))
    s.blit(imgscale, (0, 40, 480, 480))
    #prompt
    font = pygame.font.Font('segoeui.ttf', 24)
    s.blit(font.render(prompt, True, (255,255,255)), (0, 0))
    #submit
    pygame.draw.rect(s, (255, 255, 255), (310, 530, 150, 50), 3)
    s.blit(font.render("Restart", True, (255, 255,255)), (350, 537))
    #draw to screen
    screen.blit(pygame.transform.rotate(s, 90), (0,0))
    pygame.display.update()
    screen_state = "image"

# The game loop
running = True
lastPosition = None
clock = pygame.time.Clock()

while running:
    time_delta = clock.tick(60)/1000.0
    # Check for events
    for event in pygame.event.get():
        # Check for finger inputs
        if event.type == pygame.FINGERDOWN or event.type == pygame.FINGERMOTION:
            pos = (event.x * size[0], event.y * size[1])
            if clear.collidepoint(pos):
                print("Clearing")
                setup_draw()
            elif submit.collidepoint(pos):
                if screen_state == "draw":
                    print("submitting")
                    submit_pic()
                elif screen_state == "image":
                    print("new image")
                    prompt = get_prompt()
                    setup_draw()
            elif new_prompt.collidepoint(pos):
                print("new prompt")
                prompt = get_prompt()
                setup_draw()
            elif not canvas.collidepoint(pos):
                lastPosition = None
            elif lastPosition is None:
                lastPosition = pos
            else:
                pygame.draw.line(screen, (255,255,255), lastPosition, pos, 3)
                lastPosition = pos
                pygame.display.update()
        elif event.type == pygame.FINGERUP:
            if lastPosition is None:
                continue
            pos = (event.x * size[0], event.y * size[1])
            if canvas.collidepoint(pos):
                pygame.draw.line(screen, (255,255,255), lastPosition, pos, 3)
                pygame.display.update()
            lastPosition = None