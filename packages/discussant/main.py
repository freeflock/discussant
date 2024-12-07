import os
import traceback
from time import sleep

from langchain import hub
from langchain_openai import ChatOpenAI
from loguru import logger
from ratatosk_errands.adapter import Rabbit
from ratatosk_errands.model import Errand, ChatReply, Echo, PromptTemplateInstructions

RABBIT_HOST = os.getenv("RABBIT_HOST")
RABBIT_PORT = int(os.getenv("RABBIT_PORT"))
RABBIT_USERNAME = os.getenv("RABBIT_USERNAME")
RABBIT_PASSWORD = os.getenv("RABBIT_PASSWORD")


def receive_prompt_template_errand(channel, method, properties, body):
    try:
        logger.info(f"( ) receiving errand: {body}")
        errand = Errand.model_validate_json(body)
        if not isinstance(errand.instructions, PromptTemplateInstructions):
            raise ValueError(f"unknown errand instructions on errand: {errand}")

        logger.info(f"running inference")
        prompt = hub.pull(errand.instructions.prompt_name)
        model = ChatOpenAI(model="o1-preview")
        chain = prompt | model
        output = chain.invoke(errand.instructions.input_variables)
        logger.info(f"emitting echo")
        reply = ChatReply(message=output.content)
        echo = Echo(errand=errand, reply=reply)
        channel.basic_publish(exchange="", routing_key="echo", body=echo.model_dump_json())

        logger.info(f"(*) completed errand: {errand.errand_identifier}")
    except Exception as error:
        logger.error(f"(!) errand failed with error: {error}")
    finally:
        channel.basic_ack(delivery_tag=method.delivery_tag)


def main():
    while True:
        try:
            with Rabbit(RABBIT_HOST, RABBIT_PORT, RABBIT_USERNAME, RABBIT_PASSWORD) as rabbit:
                rabbit.channel.basic_qos(prefetch_count=1)
                rabbit.channel.queue_declare(queue="echo")
                rabbit.channel.queue_declare(queue="prompt_template")
                rabbit.channel.basic_consume(queue="prompt_template",
                                             on_message_callback=receive_prompt_template_errand)
                logger.info(f"setup complete, listening for errands")
                rabbit.channel.start_consuming()
        except Exception as error:
            logger.error(f"(!) rabbit connection failed with error: {error}\n{traceback.format_exc()}")
            sleep(3)


if __name__ == '__main__':
    main()
