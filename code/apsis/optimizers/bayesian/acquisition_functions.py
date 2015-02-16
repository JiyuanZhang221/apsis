from abc import ABCMeta, abstractmethod
import numpy as np
import scipy.optimize
import logging
from scipy.stats import multivariate_normal
from apsis.models.parameter_definition import NumericParamDef, PositionParamDef
import random
from apsis.utilities.logging_utils import get_logger

class AcquisitionFunction(object):
    """
    An acquisition function is used to decide which point to evaluate next.

    For a detailed explanation, see for example "A Tutorial on Bayesian
    Optimization of Expensive Cost Functions, with Application to Active User
    Modeling and Hierarchical Reinforcement Learning", Brochu et.al., 2010
    In general, each acquisition function implements two functions, evaluate
    and compute_max.
    """
    __metaclass__ = ABCMeta

    logger = None
    params = None
    LOG_FILE_NAME = "acquisition_functions.log"
    debug_file_handler = None

    def __init__(self, params=None):
        self.logger = get_logger(self, specific_log_name=self.LOG_FILE_NAME)

        self.params = params

        if self.params is None:
            self.params = {}

    @abstractmethod
    def evaluate(self, x, gp, experiment):
        """
        Evaluates the gp on the point x.

        Parameters
        ----------
        x :
        :param x:
        :param gp:
        :param experiment:
        :return:
        """
        pass

    def _compute_minimizing_evaluate(self, x, gp, experiment):
        """
        One problem is that, as a standard, scipy.optimize only searches
        minima. This means we have to convert each acquisition function to
        the minima meaning the best result.
        This the function to do so. Each compute_max can therefore just call
        this function, and know that the returned function has the best value
        as a global minimum.
        As a standard - as here - the function is returned unchanged. If you
        require a negated evaluate function, you have to change this.

        Function signature is as evaluate.
        """
        value = self.evaluate(x, gp, experiment)
        return value

    def compute_proposals(self, gp, experiment, number_proposals=1,
                          random_steps=1000):
        """
        This computes a number of proposals for candidates next to evaluate.

        The first returned proposal is the one maximizing the acquisition
        function, while the rest are randomly chosen proportional to their
         acquisition function value.

        Optimization over the acquisition function is done via random search.

        Parameters
        ----------
        gp: GPy gaussian process
            The gaussian process to use as a basis

        experiment: Experiment
            The experiment for which to find new proposals

        number_proposals=1: int
            The number of proposals to return.

        random_steps=1000: int
            The number of random steps to try out. Must be greater than
            number_proposals, ideally much greater.

        Returns
        -------
        proposals: list of Candidates
            The list of proposals to try next. The first proposal in that list
            will always be the one maximizing the acquisition function,
            followed by an unordered list of points.
        """
        evaluated_params = []
        evaluated_acq_scores = []
        sum_acq = []

        best_param_idx = 0
        best_score = float("inf")
        param_defs = experiment.parameter_definitions

        param_names = sorted(param_defs.keys())

        random_steps = max(random_steps, number_proposals)

        for i in range(random_steps):
            param_dict_eval = {}
            for pn in param_names:
                pdef = param_defs[pn]
                if isinstance(pdef, NumericParamDef) \
                        or isinstance(pdef, PositionParamDef):
                    param_dict_eval[pn] = random.random()
                else:
                    message = ("Tried using an acquisition function on "
                               "%s, which is an object of type %s."
                               "Only "
                               "NumericParamDef are supported."
                               %(str(pdef), str(type(pdef))))
                    self.logger.exception(message)
                    raise TypeError(message)

            score = self._compute_minimizing_evaluate(param_dict_eval, gp, experiment)

            if score < best_score:
                best_param_idx = i
                best_score = score
            evaluated_params.append(param_dict_eval)
            evaluated_acq_scores.append(score)
            if len(sum_acq) > 0:
                sum_acq.append(score + sum_acq[-1])
            else:
                sum_acq.append(score)

        proposals = []
        proposals.append(evaluated_params[best_param_idx])
        while len(proposals) < number_proposals:
            next_prop_idx = 0
            sum_rand = random.uniform(0, sum_acq[-1])
            while sum_rand < sum_acq[next_prop_idx]:
                next_prop_idx += 1
            proposals.append(evaluated_params[next_prop_idx])
        self.logger.info("New proposals have been calculated. They are %s"
                         %proposals)
        return proposals

    def _translate_dict_vector(self, x):
        """
        We translate from a dictionary to a list format for a point's params.

        Parameters
        ----------
        x : dictionary of string keys
            The dictionary defining the point's param values.

        Returns
        -------
        param_to_eval : vector
            Vector of the points' parameter values in order of key.
        """
        param_to_eval = []
        param_names = sorted(x.keys())
        for pn in param_names:
            param_to_eval.append(x[pn])

        return param_to_eval

    def _translate_vector_dict(self, x_vector, param_names):
        """
        We translate from a vector format to a dictionary of a point's params.

        Parameters
        ----------
        x_vector : vector
            Vector of the points' parameter values. They are assumed to be
             in order of key.

        Returns
        -------
        x : dictionary of string keys
            The dictionary defining the point's param values.
        """
        x_dict = {}

        param_names_sorted = sorted(param_names)
        for i, pn in enumerate(param_names_sorted):
            x_dict[pn] = x_vector[i]

        return x_dict

    def _translate_vector_nd_array(self, x_vec):
        """
        We translate from a vector of x_vec's params to a numpy nd_array.

        Parameters
        ----------
        x_vec : vector
            Vector of the points' parameter values. They are assumed to be
             in order of key.

        Returns
        -------
        param_nd_array : numpy nd_array
            nd_array of the points' parameter values. They are assumed to be
            in order of key.
        """
        param_nd_array = np.zeros((1, len(x_vec)))
        for i in range(len(x_vec)):
            #print (x_vec)
            param_nd_array[0,i] = x_vec[i]

        return param_nd_array


class ExpectedImprovement(AcquisitionFunction):
    """
    Implements the Expected Improvement acquisition function.
    See page 13 of "A Tutorial on Bayesian Optimization of Expensive Cost
    Functions, with Application to Active User Modeling and Hierarchical
    Reinforcement Learning", Brochu et. al., 2010.
    """
    exploitation_exploration_tradeoff = 0


    def __init__(self, params=None):
        """
        Initializes the EI instance.

        Parameters: dict of string keys
            Defines behaviour of the function. Includes:
            exploitation_tradeoff: float
                See Brochu, page 14.
            Also see AcquisitionFunction for other parameters.
        """
        super(ExpectedImprovement, self).__init__(params)
        if params is None:
            params = {}
        self.exploitation_exploration_tradeoff = params.get(
            "exploitation_tradeoff", 0)

    def _compute_minimizing_evaluate(self, x, gp, experiment):
        """
        Changes the sign of the evaluate function.
        """
        if isinstance(x, dict):
            value = self.evaluate(x, gp, experiment)
        #otherwise assume vector
        else:
            value, _ = self._evaluate_vector(x, gp, experiment)

        return -value

    def _compute_minimizing_gradient(self, x, gp, experiment):
        """
        Compute the gradient of EI if we want to minimize its negation

        Parameters
        ----------
        x : dictionary or vector
            The point for which we'd like to get the gradient.
        gp : GPy gp
            The process on which to evaluate the point on.
        experiment : experiment
            Some acquisition functions require more information about the
            experiment.

        Results
        -------
        min_gradient :

        """
        #TODO: find format of the result
        if isinstance(x, dict):
            value, gradient = self.evaluate(x, gp, experiment)
        else:
            value, gradient = self._evaluate_vector(x, gp, experiment)

        return -1 * gradient

    def _evaluate_vector(self, x_vec, gp, experiment):
        """
        Evaluates the value of the gp at the point x_vec.

        Parameters
        ----------
        x_vec : vector
            The vector defining the point.
        gp : GPy gp
            The gp on which to evaluate
        experiment : experiment
            Some acquisition functions require more information about the
            experiment.

        Results
        -------
        ei_value : vector
            The value of this acquisition funciton on the point.
        ei_gradient : vector
            The value of the gradient on the point
        """
        x_value = self._translate_vector_nd_array(x_vec)

        #mean, variance and their gradients
        mean, variance = gp.predict(x_value)
        gradient_mean, gradient_variance = gp.predictive_gradients(x_value)

        #gpy does everythin in matrices
        gradient_mean = gradient_mean[0]
        #gpy returns variance in row matrices.
        gradient_variance = np.transpose(gradient_variance)

        #these values should be real scalars!
        mean = mean[0][0]
        variance = variance[0][0]

        std_dev = variance ** 0.5

        #Formula adopted from the phd thesis of Jasper Snoek page 48 with
        # \gamma equals Z here
        #Additionally support for the exploration exploitation trade-off
        #as suggested by Brochu et al.
        x_best = experiment.best_candidate.result

        #handle case of maximization
        sign = 1
        if not experiment.minimization_problem:
            sign = -1

        z_numerator = sign * (x_best - mean +
                              self.exploitation_exploration_tradeoff)

        ei_value = 0
        ei_gradient = 0
        if std_dev != 0:
            z = float(z_numerator) / std_dev

            cdf_z = scipy.stats.norm().cdf(z)
            pdf_z = scipy.stats.norm().pdf(z)

            ei_value = z_numerator * cdf_z + std_dev * pdf_z

            #compute ei gradient
            #new implementation based on own derivation
            ei_gradient_part1 = (1/(2*variance)) * ei_value * gradient_variance
            ei_gradient_part2 = -1 * sign * gradient_mean * cdf_z
            ei_gradient_part3 = -1 * gradient_variance * cdf_z * z * (1/(2*std_dev))
            ei_gradient = ei_gradient_part1 + ei_gradient_part2 + ei_gradient_part3

            ei_gradient = np.transpose(ei_gradient)[0]

        return ei_value, ei_gradient

    def _evaluate_vector_gradient(self, x_vec, gp, experiment):
        """
        Evaluates the gradoemt of the gp at the point x_vec.

        Parameters
        ----------
        x_vec : vector
            The vector defining the point.
        gp : GPy gp
            The gp on which to evaluate
        experiment : experiment
            Some acquisition functions require more information about the
            experiment.

        Results
        -------
        gradient : vector
            The value of the gradient on the point
        """
        value, grad = self._evaluate_vector(x_vec, gp, experiment)

        return grad

    def evaluate(self, x, gp, experiment):
        x_value = self._translate_dict_vector(x)
        value, gradient = self._evaluate_vector(x_value, gp, experiment)
        return value


    def compute_proposals(self, gp, experiment, number_proposals=1,
                          random_steps=1000):
        random_proposals = super(ExpectedImprovement, self).compute_proposals(
            gp=gp, experiment=experiment, number_proposals=number_proposals,
            random_steps=random_steps)

        optimizer = self.params.get('optimization', 'random')
        if(optimizer == 'random'):
            return random_proposals

        #we have only one else case here, where we use bfgs at the moment,
        #therefore no else right now for readability.

        #do a scipy minimize, use bfgs since we only have gradient, no hessian
        #initial guess is the best found by random search
        initial_guess = self._translate_dict_vector(random_proposals[0])

        result = scipy.optimize.minimize(self._compute_minimizing_evaluate,
                                         x0=initial_guess, method='BFGS',
                                         jac=self._compute_minimizing_gradient,
                                         options={'disp': True}, args=tuple([gp, experiment]))
        x_min = result.x
        f_min = result.fun
        num_f_steps = result.nfev
        num_grad_steps = result.njev
        success = result.success

        #Extensive Debug Logging to Debug Acquisition Optimization
        #self.logger.level=logging.DEBUG
        self.logger.debug("BFGS EI Optimization finished.")
        self.logger.debug("\tx_min: " + str(x_min))
        self.logger.debug("\tf_min: " + str(f_min))
        self.logger.debug("\tNum f evaluations: " + str(num_f_steps))
        self.logger.debug("\tNum grad(f) evaluations: " + str(num_grad_steps))
        self.logger.debug("RandomSearch")
        if self.logger.level == logging.DEBUG:
            rand_f_min = self._compute_minimizing_evaluate(random_proposals[0], gp, experiment)
            self.logger.debug("\tx_min " + str(random_proposals[0]))
            self.logger.debug("\tf_min " + str(rand_f_min))

        #deal with result, eventually take random then
        #when using scipy.optimize.minimize use the success flag
        if not success:
            self.logger.warning("BFGS Optimization failed. Using result from RandomSearch.")

        else:
            #remove the last entry from random_proposals and add the new one at
            #first place
            del random_proposals[-1]
            param_names = experiment.parameter_definitions.keys()
            x_min_dict = self._translate_vector_dict(x_min, param_names)

            random_proposals.insert(0, x_min_dict)

        return random_proposals


class ProbabilityOfImprovement(AcquisitionFunction):
    """
    Implements the probability of improvement function.

    See page 12 of "A Tutorial on Bayesian Optimization of Expensive Cost
    Functions, with Application to Active User Modeling and Hierarchical
    Reinforcement Learning", Brochu et. al., 2010.
    """

    def evaluate(self, x, gp, experiment):
        """
        Evaluates the function.
        """

        dimensions = len(experiment.parameter_definitions)
        x_value = self._translate_dict_vector(x)

        mean, variance = gp.predict(x_value)

        # do not standardize on our own, but use the mean, and covariance
        # we get from the gp
        stdv = variance ** 0.5
        x_best = experiment.best_candidate.result
        z = (x_best - mean)/stdv

        cdf = scipy.stats.norm().cdf(z)
        result = cdf
        if not experiment.minimization_problem:
            result = 1 - cdf
        return result

    def _compute_minimizing_evaluate(self, x, gp, experiment):
        """
        Changes the sign of the evaluate function.
        """
        value = self.evaluate(x, gp, experiment=experiment)
        value = -value

        return value