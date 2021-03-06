#!/usr/bin/env python

from stable_baselines.common.atari_wrappers import make_atari, wrap_deepmind
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


env = make_atari('BreakoutNoFrameskip-v4')
env = wrap_deepmind(env, frame_stack=True, scale=True)
env.seed(50)


path = 'model/output_delay_save.txt'
f = open(path, 'w')

actions_list = 4
def create_q_model():
    inputs = layers.Input(shape=(84, 84, 4,))
    layer1 = layers.Conv2D(32, 8, strides=4, activation="relu")(inputs)
    layer2 = layers.Conv2D(64, 4, strides=2, activation="relu")(layer1)
    layer3 = layers.Conv2D(64, 3, strides=1, activation="relu")(layer2)
    layer4 = layers.Flatten()(layer3)
    layer5 = layers.Dense(512, activation="relu")(layer4)
    action = layers.Dense(actions_list, activation="linear")(layer5)

    return keras.Model(inputs=inputs, outputs=action)


model = create_q_model()
model_target = create_q_model()
model.summary()

optimizer = keras.optimizers.Adam(learning_rate=0.00025, clipnorm=1.0) # 必須很小

epsilon = 1.0 
cur_frame = 0
frame_push = 4
target_push = 2000
num_episode = 50000
cur_episode = 0
mean_reward = 0

loss_function = keras.losses.Huber()

action_history = []
state_history = []
state_next_history = []
rewards_history = []
done_history = []
episode_reward_history = []

reward_list = []

while True: 
    if cur_episode >= num_episode:
        break
    print()
    print('cur episode: ', cur_episode)
    
    cur_episode += 1
    state = np.array(env.reset())
    episode_reward = 0

    for timestep in range(1, 10000):
        check = 0
        cur_frame += 1

        for r in reward_list:
            r[0] = r[0]-1

       
        if cur_frame < 10000 or epsilon > np.random.rand(1)[0]:
            action = np.random.choice(actions_list)
        else:
            state_tensor = tf.convert_to_tensor(state)
            state_tensor = tf.expand_dims(state_tensor, 0)
            action_probs = model(state_tensor, training=False)
            action = tf.argmax(action_probs[0]).numpy()

      
        epsilon -= 0.9 / 200000.0
        epsilon = max(epsilon, 0.1)
        state_next, reward, done, _ = env.step(action)
        state_next = np.array(state_next)
        episode_reward += reward

        # episode_reward += reward
        if reward > 0:
            reward_list.append([35,reward])
            if(len(reward_list) > 1):
                reward_list[0][0] = 0
            print(reward_list)

        if len(reward_list) > 0 and reward_list[0][0] <= 0:
            episode_reward = episode_reward + reward_list[0][1]
            rewards_history.append(reward_list[0][1])
            reward_list.pop(0)
        else:
            rewards_history.append(0)

        action_history.append(action)
        state_history.append(state)
        state_next_history.append(state_next)
        done_history.append(done)
        # rewards_history.append(reward)
        state = state_next

        if cur_frame % frame_push == 0 and len(done_history) > 32:

            indices = np.random.choice(range(len(done_history)), size=32)

            state_sample = np.array([state_history[i] for i in indices])
            state_next_sample = np.array([state_next_history[i] for i in indices])
            rewards_sample = [rewards_history[i] for i in indices]
            action_sample = [action_history[i] for i in indices]
            done_sample = tf.convert_to_tensor([float(done_history[i]) for i in indices])

            future_rewards = model_target.predict(state_next_sample)
            updated_q_values = rewards_sample + 0.99  * tf.reduce_max(future_rewards, axis=1)
            updated_q_values = updated_q_values * (1 - done_sample) - done_sample
            masks = tf.one_hot(action_sample, actions_list)

            with tf.GradientTape() as tape:
                check = 1
                q_values = model(state_sample)

                q_action = tf.reduce_sum(tf.multiply(q_values, masks), axis=1)
                loss = loss_function.(updated_q_values, q_action)

            grads = tape.gradient(loss, model.trainable_variables)
            optimizer.apply_gradients(zip(grads, model.trainable_variables))

        if cur_frame % 2000 == 0:
            model_target.set_weights(model.get_weights())

        if len(rewards_history) > 100000:
            del rewards_history[:1]
            del state_history[:1]
            del state_next_history[:1]
            del action_history[:1]
            del done_history[:1]

        if done:
            reward_list = []
            break

    if check:
        print("episode:",cur_episode-1,"reward:", episode_reward, "loss:", float(loss))
    else:
        print("episode:",cur_episode-1,"reward:", episode_reward)
    episode_reward_history.append(episode_reward)
    if len(episode_reward_history) > 30:
        del episode_reward_history[:1]
    mean_reward = np.mean(episode_reward_history)
    if check:
        f.write(str(cur_episode)+", "+str(mean_reward)+", "+str(float(loss)))
    else:
        f.write(str(cur_episode)+", "+str(mean_reward))
    f.write('\n')
    model.save('model/my_model_delay.h5')

f.close()
