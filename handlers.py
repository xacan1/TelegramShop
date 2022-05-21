from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery, LabeledPrice, PreCheckoutQuery, ContentType
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text, Command, state
# from keyboards import *
import config
import services
from main import dp


class FSMOrder(state.StatesGroup):
    ask_about_create_order = state.State()
    input_first_name = state.State()
    input_last_name = state.State()
    input_phone = state.State()
    ask_about_comment = state.State()
    input_comment = state.State()


class FSMAddProductToCart(state.StatesGroup):
    input_code_product = state.State()
    input_quantity = state.State()
    input_warehouse = state.State()


class FSMDeleteProductToCart(state.StatesGroup):
    confirm_delete = state.State()


class FSMDeleteProductFromOrder(state.StatesGroup):
    confirm_delete = state.State()


# Реакция на текст в сообщении
@dp.message_handler(Text('Привет'))
async def sey_hello(message: Message):
    username = message['from']['first_name'] if message.text else ''
    await message.answer(f"{message.text} {username}, твой id={message['from']['id']}")


# Reply Кнопки для опроса
# @dp.message_handler(Command('shop'))
# async def show_shop(message: Message):
#     await message.answer('Shop', reply_markup=keyboard)


@dp.message_handler(Text(equals=['Кнопка 1', 'Кнопка 2', 'Кнопка 3']))
async def get_goods(message: Message):
    await message.answer(f'Нажата: {message.text}', reply_markup=ReplyKeyboardRemove())


# Рабочий магазин

@dp.message_handler(Command(['start', 'help']))
async def start_message(message: Message):
    await message.answer(text='Добро пожаловать в магазин Барахло Шоп!',
                         reply_markup=await services.get_start_menu())


@dp.message_handler(Command('📦Товары'))
async def show_products(message: Message):
    kb_categories = await services.get_categories()
    await message.answer('Выберите категорию товара:', reply_markup=kb_categories)


@dp.message_handler(Command('🛒Корзина'))
async def show_cart(message: Message):
    cart_info = await services.get_cart(message.from_user.id)

    if cart_info['amount_cart'] == 0:
        await message.answer('Корзина пуста')
        return

    await message.answer('Товары в корзине:')

    for product in cart_info:
        if product != 'amount_cart':
            await message.answer(product, reply_markup=cart_info[product])

    await message.answer(f'Общая сумма товаров: {cart_info["amount_cart"]:10.2f}')


@dp.callback_query_handler(text_contains='cancel')
async def cancel(call: CallbackQuery):
    # await call.answer('Отмена', show_alert=True)
    # await call.message.edit_text('...')
    # await call.message.edit_reply_markup(reply_markup=None)
    await call.message.delete()


@dp.callback_query_handler(lambda cq: 'category_nested_pk' in cq.data)
async def get_subcategory_list(call: CallbackQuery):
    await call.answer(cache_time=60)
    subcategory_pk = call.data.replace('category_nested_pk', '')
    kb_subcategories = await services.get_categories(subcategory_pk)
    await call.message.answer(text='Выберите подкатегорию:', reply_markup=kb_subcategories)


@dp.callback_query_handler(lambda cq: 'category_pk' in cq.data)
async def get_product_list(call: CallbackQuery):
    await call.answer(cache_time=60)
    category_pk = call.data.replace('category_pk', '')
    kb_products = await services.get_product_list(category_pk)
    await call.message.answer(text='Выберите товар:', reply_markup=kb_products)


@dp.callback_query_handler(lambda cq: 'show_product' in cq.data)
async def get_product(call: CallbackQuery):
    await call.answer(cache_time=60)
    product_pk = call.data.replace('show_product', '')
    kb_show_product, result_str, url_photo = await services.get_product_info(product_pk)
    await call.message.answer(f'{url_photo}\n{result_str}', reply_markup=kb_show_product)


# @dp.callback_query_handler(lambda cq: 'back_to_category' in cq.data)
# async def get_


# Начало диалога добавления товара в Корзину
# **********************************************************************************************************************
# Начнем с кнопки подтверждения выбора, для проброса кода товара в запрос к БД
@dp.callback_query_handler(lambda cq: 'add_product_to_cart' in cq.data, state=None)
async def add_product_to_cart(call: CallbackQuery):
    product_pk = call.data.replace('add_product_to_cart', '')
    await FSMAddProductToCart.input_code_product.set()
    await call.message.answer('Добавить в корзину?', reply_markup=await services.get_confirm_add_product_to_cart(product_pk))


# если нажали "нет", то завершим машинное состояние
@dp.callback_query_handler(lambda cq: 'not_confirm_add_product_to_cart' in cq.data, state=FSMAddProductToCart.input_code_product)
async def confirm_product(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.edit_text('Товар не добавлен', reply_markup=None)


@dp.callback_query_handler(lambda cq: 'confirm_add_product_to_cart' in cq.data, state=FSMAddProductToCart.input_code_product)
async def confirm_product(call: CallbackQuery, state: FSMContext):
    product_pk = call.data.replace('confirm_add_product_to_cart', '')

    async with state.proxy() as data:
        data['product_pk'] = product_pk

    await FSMAddProductToCart.next()
    await call.message.answer('Укажите требуемое количество:', reply_markup=ReplyKeyboardRemove())


@dp.message_handler(state=FSMAddProductToCart.input_quantity)
async def input_quantity(message: Message, state: FSMContext):
    async with state.proxy() as data:
        if not message.text.isdigit():
            await message.answer('Вы ввели не корректное число. Укажите ещё раз количество:')
            return

        data['quantity'] = message.text
        data['id_messenger'] = message.from_user.id
        product_pk = data['product_pk']

    await FSMAddProductToCart.next()
    await message.answer('Выберите склад из списка:', reply_markup=await services.get_warehouses_kb(product_pk, message.text))


@dp.callback_query_handler(lambda cq: 'warehouse_pk' in cq.data, state=FSMAddProductToCart.input_warehouse)
async def input_warehouse(call: CallbackQuery, state: FSMContext):
    warehouse_pk = call.data.replace('warehouse_pk', '')
    # что бы два раза пользователь не нажимал кнопку и не плодил дубли
    await call.message.delete()

    async with state.proxy() as data:
        data['warehouse_pk'] = warehouse_pk
        # пишем данные в БД корзины и словареподобный объект <class 'aiogram.dispatcher.storage.FSMContextProxy'> легко распаковывается в обычный словарь
        product_cart_new = {**data}
        await services.add_product_to_cart(product_cart_new)
        await call.message.answer('Товар добавлен в корзину', reply_markup=await services.get_start_menu())

    await state.finish()


# Конец диалога добавления в корзину
# **************************************************************************************************************


# Начало диалога удаления товара из корзины
# **************************************************************************************************************
@dp.callback_query_handler(lambda cq: 'delete_product_from_cart' in cq.data, state=None)
async def delete_product_from_cart(call: CallbackQuery, state: FSMContext):
    await call.answer(cache_time=60)
    await FSMDeleteProductToCart.confirm_delete.set()
    product_pk = call.data.replace('delete_product_from_cart', '')

    async with state.proxy() as data:
        data['product_pk'] = product_pk

    await call.message.answer('Удалить товар из корзины?', reply_markup=await services.get_answer_yes_no_kb())


# если нажали "нет", то завершим машинное состояние
@dp.callback_query_handler(lambda cq: 'answer_yes_no0' in cq.data, state=FSMDeleteProductToCart.confirm_delete)
async def confirm_product(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.delete()
    await call.message.answer('Товар остался в корзине', reply_markup=await services.get_start_menu())


@dp.callback_query_handler(lambda cq: 'answer_yes_no1' in cq.data, state=FSMDeleteProductToCart.confirm_delete)
async def confirm_product(call: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        product_cart_info = {
            'product_pk': data['product_pk'],
            'id_messenger': call.from_user.id
        }

    await services.delete_product_from_cart(product_cart_info)
    await state.finish()
    await call.message.answer('Товар удален из корзины', reply_markup=await services.get_start_menu())


# Конец диалога удаления товара из корзины
# **************************************************************************************************************


# Начало диалога оформления Заказа через машинные состояния
# **************************************************************************************************************
@dp.message_handler(Command('🧾Заказ'), state=None)
async def ask_about_create_order(message: Message):
    cart_empty = await services.checkCart(message.from_user.id)

    if cart_empty:
        await message.answer('Ваша корзина пуста, для создания заказа нужно добавить в корзину товары')
        return

    await FSMOrder.ask_about_create_order.set()
    await message.answer('Желаете оформить заказ?', reply_markup=await services.get_answer_yes_no_kb())


@dp.callback_query_handler(lambda cq: 'answer_yes_no' in cq.data, state=FSMOrder.ask_about_create_order)
async def add_product(call: CallbackQuery, state: FSMContext):
    answer = call.data.replace('answer_yes_no', '')

    if answer == '1':
        await FSMOrder.next()
        await call.message.answer('Укажите имя:', reply_markup=ReplyKeyboardRemove())
    else:
        await call.message.delete()
        await state.finish()


# Ловим первый ответ пользователя
@dp.message_handler(state=FSMOrder.input_first_name)
async def input_first_name(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['first_name'] = message.text

    await FSMOrder.next()
    await message.answer('Укажите фамилию:', reply_markup=ReplyKeyboardRemove())


# Ловим второй ответ
@dp.message_handler(state=FSMOrder.input_last_name)
async def input_last_name(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['last_name'] = message.text

    await FSMOrder.next()
    await message.answer('Отправьте свой номер нажатием на кнопку:', reply_markup=await services.get_contact_kb())


# Ловим третий ответ
@dp.message_handler(content_types=['contact'], state=FSMOrder.input_phone)
async def get_contact(message: Message, state: FSMContext):
    async with state.proxy() as data:
        data['phone'] = message.contact.phone_number
        data['id_messenger'] = message.contact.user_id

    await FSMOrder.next()
    await message.answer('Желаете оставить комментарий к заказу?', reply_markup=await services.get_answer_yes_no_kb())


@dp.callback_query_handler(lambda cq: 'answer_yes_no' in cq.data, state=FSMOrder.ask_about_comment)
async def get_comment(call: CallbackQuery, state: FSMContext):
    answer = call.data.replace('answer_yes_no', '')

    if answer == '1':
        await FSMOrder.next()
        await call.message.answer('Оставьте комментарий:', reply_markup=ReplyKeyboardRemove())
    else:
        async with state.proxy() as data:
            order_info = {**data}
            await call.message.answer('Спасибо за Ваш заказ! Оплатите и ожидайте звонка от сотрудника магазина.', reply_markup=await services.get_start_menu())
            # order_info = await services.create_order(order_info)
            # prices = [LabeledPrice('Руб', int(order_info['amount']) * 100), ]
            order_info['id'] = 0
            prices = [LabeledPrice('Руб', 99900), ]

            await call.bot.send_invoice(
                chat_id=call.message.chat.id,
                title='Заказ',
                description='Покупка товаров в магазине',
                payload=f"order №{order_info['id']}",
                provider_token=config.PROVIDER_TOKEN,
                currency='RUB',
                prices=prices,
                start_parameter='test',
            )

        await state.finish()


# Подтверждат что товар есть на складе для проведения платежа
@dp.pre_checkout_query_handler()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.bot.answer_pre_checkout_query(pre_checkout_query.id, True)


# обработаем принятый платеж
@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
async def process_pay(message: Message):
    if 'order №' in message.successful_payment.invoice_payload:
        await message.answer('Оплата прошла успешно!', reply_markup=await services.get_start_menu())


# Ловим последний ответ, если он есть
@dp.message_handler(state=FSMOrder.input_comment)
async def input_comment(message: Message, state: FSMContext):

    async with state.proxy() as data:
        data['comment'] = message.text
        order_info = {**data}
        await message.answer('Спасибо за Ваш заказ! Оплатите и ожидайте звонка от сотрудника магазина.', reply_markup=await services.get_start_menu())
        await services.create_order(order_info)

    await state.finish()


# @dp.message_handler(lambda cq: 'payment_yookassa' in cq.data)


# Конец диалога оформления Заказа
# **********************************************************************************************************************


# Показать список заказов покупателя
@dp.message_handler(Command('💼История_заказов'))
async def get_order_list(message: Message):
    kb_orders = await services.get_order_list(message.from_user.id)

    if not kb_orders:
        await message.answer('У Вас ещё не было заказов, но это легко исправить ;)')
        return

    await message.answer('Ваши заказы:', reply_markup=kb_orders)


# Показать заказ покупателя
@dp.callback_query_handler(lambda cq: 'order_pk' in cq.data)
async def get_order(call: CallbackQuery):
    order_pk = call.data.replace('order_pk', '')
    order_products, order_info = await services.get_order(order_pk)

    if not order_products:
        await call.message.answer('Заказ пуст')
        return

    if order_info:
        await call.message.answer(
            f"{order_info['order']} на сумму {order_info['amount']}\nСтатус заказа: {order_info['status']['repr']}\nДоставка: {order_info['delivery_type']['repr']}\nТип оплаты: {order_info['payment_type']['repr']}\nТовары в заказе:"
        )

    for product in order_products:
        await call.message.answer(product, reply_markup=order_products[product])


# Начало диалога удаления товара из заказа
# **************************************************************************************************************
@dp.callback_query_handler(lambda cq: 'delete_product_from_order' in cq.data, state=None)
async def delete_product_from_cart(call: CallbackQuery, state: FSMContext):
    await call.answer(cache_time=60)
    await FSMDeleteProductFromOrder.confirm_delete.set()
    param_list = call.data.replace('delete_product_from_order', '').split(':')
    product_pk = param_list[0]
    order_pk = param_list[1]

    async with state.proxy() as data:
        data['product_pk'] = product_pk
        data['order_pk'] = order_pk

    await call.message.answer('Удалить товар из заказа?', reply_markup=await services.get_answer_yes_no_kb())


# если нажали "нет", то завершим машинное состояние
@dp.callback_query_handler(lambda cq: 'answer_yes_no0' in cq.data, state=FSMDeleteProductFromOrder.confirm_delete)
async def confirm_product(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.delete()
    await call.message.answer('Товар остался в заказе', reply_markup=await services.get_start_menu())


@dp.callback_query_handler(lambda cq: 'answer_yes_no1' in cq.data, state=FSMDeleteProductFromOrder.confirm_delete)
async def confirm_product(call: CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        product_cart_info = {
            'product_pk': data['product_pk'],
            'order_pk': data['order_pk'],
            'id_messenger': call.from_user.id
        }

    await services.delete_product_from_order(product_cart_info)
    await state.finish()
    await call.message.answer('Товар удален из заказа', reply_markup=await services.get_start_menu())


# Конец диалога удаления товара из заказа
# **************************************************************************************************************
