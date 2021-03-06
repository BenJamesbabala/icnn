# Code from Repo SimonRamstedt/ddpg
# Heavily modified

import os
import pprint

import gym
import numpy as np
import tensorflow as tf

import agent
import normalized_env
import runtime_env

flags = tf.app.flags
FLAGS = flags.FLAGS
flags.DEFINE_string('env', '', 'gym environment')
flags.DEFINE_string('outdir', 'output', 'output directory')
flags.DEFINE_boolean('force', False, 'overwrite existing results')
flags.DEFINE_integer('train', 1000, 'training timesteps between testing episodes')
flags.DEFINE_integer('test', 1, 'testing episodes between training timesteps')
flags.DEFINE_integer('tmax', 1000, 'maxium timesteps each episode')
flags.DEFINE_integer('total', 100000, 'total training timesteps')
flags.DEFINE_float('monitor', 0.01, 'probability of monitoring a test episode')
flags.DEFINE_string('model', 'ICNN', 'reinforcement learning model[DDPG, NAF, ICNN]')
flags.DEFINE_integer('tfseed', 0, 'random seed for tensorflow')
flags.DEFINE_integer('gymseed', 0, 'random seed for openai gym')
flags.DEFINE_integer('npseed', 0, 'random seed for numpy')

if FLAGS.model == 'DDPG':
    import ddpg
    Agent = ddpg.Agent
elif FLAGS.model == 'NAF':
    import naf
    Agent = naf.Agent
elif FLAGS.model == 'ICNN':
    import icnn
    Agent = icnn.Agent


class Experiment(object):

    def run(self):
        self.train_timestep = 0
        self.test_timestep = 0

        # create normal
        self.env = normalized_env.make_normalized_env(gym.make(FLAGS.env))
        tf.set_random_seed(FLAGS.tfseed)
        np.random.seed(FLAGS.npseed)
        self.env.monitor.start(os.path.join(FLAGS.outdir, 'monitor'), force=FLAGS.force)
        self.env.seed(FLAGS.gymseed)
        gym.logger.setLevel(gym.logging.WARNING)

        dimO = self.env.observation_space.shape
        dimA = self.env.action_space.shape
        print(dimO, dimA)
        pprint.pprint(self.env.spec.__dict__)

        self.agent = Agent(dimO, dimA=dimA)
        simple_log_file = open(os.path.join(FLAGS.outdir, 'log.txt'), 'w')

        while self.train_timestep < FLAGS.total:

            # test
            reward_list = []
            for _ in xrange(FLAGS.test):
                reward, timestep = self.run_episode(test=True, monitor=np.random.rand() < FLAGS.monitor)
                reward_list.append(reward)
                self.test_timestep += timestep
            avg_reward = np.mean(reward_list)
            print('Average test return {} after {} timestep of training.'.format(avg_reward, self.train_timestep))
            print >> simple_log_file, "{}\t{}".format(self.train_timestep, avg_reward)

            # train
            reward_list = []
            last_checkpoint = self.train_timestep / FLAGS.train
            while self.train_timestep / FLAGS.train == last_checkpoint:
                reward, timestep = self.run_episode(test=False, monitor=False)
                reward_list.append(reward)
                self.train_timestep += timestep
            avg_reward = np.mean(reward_list)
            print('Average train return {} after {} timestep of training.'.format(avg_reward, self.train_timestep))

        self.env.monitor.close()

    def run_episode(self, test=True, monitor=False):
        self.env.monitor.configure(lambda _: monitor)
        observation = self.env.reset()
        self.agent.reset(observation)
        sum_reward = 0
        timestep = 0
        term = False
        while not term:
            action = self.agent.act(test=test)

            observation, reward, term, info = self.env.step(action)
            term = (not test and timestep + 1 >= FLAGS.tmax) or term

            filtered_reward = self.env.filter_reward(reward)
            self.agent.observe(filtered_reward, term, observation, test=test)

            sum_reward += reward
            timestep += 1

        return sum_reward, timestep


def main():
    Experiment().run()

if __name__ == '__main__':
    runtime_env.run(main, FLAGS.outdir)
